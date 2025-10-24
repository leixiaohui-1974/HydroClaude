"""
非恒定流求解器全面审计

目标：
1. 梳理所有非恒定流求解器
2. 测试精度和稳定性
3. 形成明确对比和适用性结论
4. 标记需要删除的求解器
"""

import numpy as np
import sys
import os
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

print("="*80)
print("HydroClaude非恒定流求解器全面审计")
print("="*80)

# ========== 求解器清单 ==========
print("\n" + "="*80)
print("第一步：求解器清单")
print("="*80)

solvers_inventory = {
    "Canal类集成求解器": {
        "preissmann": {
            "文件": "physics/numerical_methods/preissmann_solver.py",
            "描述": "四点隐式格式（Preissmann格式）",
            "类型": "隐式有限差分",
            "接口": "physics/canal.py → PreissmannSolver"
        },
        "fvm": {
            "文件": "physics/numerical_methods/fvm_solver.py",
            "描述": "有限体积法（HLL Riemann求解器）",
            "类型": "显式有限体积",
            "接口": "physics/canal.py → FVMSolver"
        },
        "moc": {
            "文件": "physics/canal.py (内联实现)",
            "描述": "特征线法（硬编码边界条件）",
            "类型": "显式特征线",
            "接口": "physics/canal.py → update_high_fidelity"
        }
    },
    "独立求解器类": {
        "HighOrderCanalSolver": {
            "文件": "solvers/high_order_solver.py",
            "描述": "MUSCL重构 + RK2时间步进",
            "类型": "高阶有限体积",
            "接口": "HydrostaticCanalSolver子类"
        },
        "HydrostaticCanalSolver": {
            "文件": "solvers/hydrostatic_canal_solver.py",
            "描述": "静水重构 + HLL通量",
            "类型": "保well-balanced有限体积",
            "接口": "独立求解器"
        },
        "CoupledCanalSolver": {
            "文件": "solvers/coupled_canal_solver.py",
            "描述": "耦合多渠道求解器",
            "类型": "隐式耦合",
            "接口": "网络求解器"
        },
        "FVMSolver (solvers)": {
            "文件": "solvers/fvm_solver.py",
            "描述": "独立FVM求解器",
            "类型": "有限体积",
            "接口": "独立求解器"
        }
    },
    "遗留求解器 (legacy_backup)": {
        "说明": "legacy_backup目录下有多个旧版求解器，不应再使用"
    }
}

print("\n📋 已识别的非恒定流求解器：\n")
for category, solvers in solvers_inventory.items():
    print(f"【{category}】")
    if isinstance(solvers, dict):
        for name, info in solvers.items():
            if isinstance(info, dict):
                print(f"  • {name}")
                print(f"      文件: {info.get('文件', 'N/A')}")
                print(f"      描述: {info.get('描述', 'N/A')}")
                print(f"      类型: {info.get('类型', 'N/A')}")
            else:
                print(f"  • {name}: {info}")
    print()

# ========== 精度测试 ==========
print("="*80)
print("第二步：精度测试（质量守恒场景）")
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

print(f"\n测试场景:")
print(f"  入流={Q_in}m³/s, 出流={Q_out}m³/s, 时间={sim_time}s")
print(f"  理论Δh={expected_delta_h:.4f}m")
print()

# 测试结果存储
test_results = {}

# ========== 测试1: Canal Preissmann ==========
print("-" * 80)
print("测试 1/5: Canal类 - Preissmann求解器")
print("-" * 80)

from physics.canal import Canal

try:
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

    initial_h = np.mean(canal_preissmann.hydraulic_state.h)

    for k in range(n_steps):
        inputs = {
            'upstream_flow': Q_in,
            'downstream_flow': Q_out
        }
        canal_preissmann.update_high_fidelity(dt, inputs)

    final_h = np.mean(canal_preissmann.hydraulic_state.h)
    actual_dh = final_h - initial_h
    error = abs(actual_dh - expected_delta_h)
    error_pct = error / expected_delta_h * 100

    test_results['Canal-Preissmann'] = {
        'status': 'success',
        'error_pct': error_pct,
        'error_m': error,
        'actual_dh': actual_dh,
        'stable': True
    }

    print(f"✅ 成功: 误差={error_pct:.1f}%")

except Exception as e:
    test_results['Canal-Preissmann'] = {
        'status': 'failed',
        'error': str(e),
        'stable': False
    }
    print(f"❌ 失败: {e}")

# ========== 测试2: Canal FVM ==========
print("\n" + "-" * 80)
print("测试 2/5: Canal类 - FVM求解器")
print("-" * 80)

try:
    canal_fvm = Canal(
        name="test_fvm",
        volume_min=0.0,
        volume_max=canal_length * canal_width * 10,
        area=canal_width * initial_depth,
        length=canal_length,
        slope=0.001,
        n_sections=51,
        method='fvm',
        manning_n=0.025,
        width=canal_width,
        initial_depth=initial_depth,
        initial_flow=initial_flow
    )

    initial_h = np.mean(canal_fvm.hydraulic_state.h)

    stable = True
    for k in range(n_steps):
        inputs = {
            'upstream_flow': Q_in,
            'downstream_flow': Q_out
        }
        canal_fvm.update_high_fidelity(dt, inputs)

        # 检查NaN
        if np.isnan(canal_fvm.hydraulic_state.h).any():
            stable = False
            print(f"❌ NaN出现在第{k}步")
            break

    final_h = np.mean(canal_fvm.hydraulic_state.h)
    actual_dh = final_h - initial_h

    if stable and not np.isnan(final_h):
        error = abs(actual_dh - expected_delta_h)
        error_pct = error / expected_delta_h * 100

        test_results['Canal-FVM'] = {
            'status': 'success',
            'error_pct': error_pct,
            'error_m': error,
            'actual_dh': actual_dh,
            'stable': True
        }

        print(f"✅ 成功: 误差={error_pct:.1f}%")
    else:
        test_results['Canal-FVM'] = {
            'status': 'unstable',
            'error': 'Numerical overflow (NaN)',
            'stable': False
        }
        print(f"❌ 数值不稳定（NaN）")

except Exception as e:
    test_results['Canal-FVM'] = {
        'status': 'failed',
        'error': str(e),
        'stable': False
    }
    print(f"❌ 失败: {e}")

# ========== 测试3: Canal MOC ==========
print("\n" + "-" * 80)
print("测试 3/5: Canal类 - MOC求解器")
print("-" * 80)

try:
    canal_moc = Canal(
        name="test_moc",
        volume_min=0.0,
        volume_max=canal_length * canal_width * 10,
        area=canal_width * initial_depth,
        length=canal_length,
        slope=0.001,
        n_sections=51,
        method='moc',
        manning_n=0.025,
        width=canal_width,
        initial_depth=initial_depth,
        initial_flow=initial_flow
    )

    initial_h = np.mean(canal_moc.hydraulic_state.h)

    for k in range(n_steps):
        inputs = {
            'Q_in': Q_in,
            'Q_out': Q_out
        }
        canal_moc.update_high_fidelity(dt, inputs)

    final_h = np.mean(canal_moc.hydraulic_state.h)
    actual_dh = final_h - initial_h
    error = abs(actual_dh - expected_delta_h)
    error_pct = error / expected_delta_h * 100

    test_results['Canal-MOC'] = {
        'status': 'success',
        'error_pct': error_pct,
        'error_m': error,
        'actual_dh': actual_dh,
        'stable': True
    }

    print(f"✅ 成功: 误差={error_pct:.1f}%")

except Exception as e:
    test_results['Canal-MOC'] = {
        'status': 'failed',
        'error': str(e),
        'stable': False
    }
    print(f"❌ 失败: {e}")

# ========== 测试4: HighOrderCanalSolver ==========
print("\n" + "-" * 80)
print("测试 4/5: HighOrderCanalSolver (MUSCL+RK2)")
print("-" * 80)

try:
    from solvers.high_order_solver import HighOrderCanalSolver

    solver_ho = HighOrderCanalSolver(
        length=canal_length,
        nx=51,
        B=canal_width,
        S0=0.001,
        n=0.025,
        muscl_limiter='minmod'
    )

    solver_ho.h = np.ones(51) * initial_depth
    solver_ho.hu = np.ones(51) * initial_flow / canal_width

    def Q_upstream_func(t):
        return Q_in

    def h_downstream_func(t):
        return initial_depth  # 简化

    result = solver_ho.solve_transient_high_order(
        t_end=sim_time,
        dt=dt,
        Q_upstream_func=Q_upstream_func,
        h_downstream_func=h_downstream_func,
        save_interval=1,
        use_muscl=True,
        use_rk2=True,
        verbose=False
    )

    final_h = np.mean(result['h_final'])
    actual_dh = final_h - initial_depth

    if not np.isnan(final_h):
        error = abs(actual_dh - expected_delta_h)
        error_pct = error / expected_delta_h * 100

        test_results['HighOrderCanalSolver'] = {
            'status': 'success',
            'error_pct': error_pct,
            'error_m': error,
            'actual_dh': actual_dh,
            'stable': True
        }

        print(f"✅ 成功: 误差={error_pct:.1f}%")
    else:
        test_results['HighOrderCanalSolver'] = {
            'status': 'unstable',
            'error': 'Numerical overflow (NaN)',
            'stable': False
        }
        print(f"❌ 数值不稳定（NaN）")

except Exception as e:
    test_results['HighOrderCanalSolver'] = {
        'status': 'failed',
        'error': str(e),
        'stable': False
    }
    print(f"❌ 失败: {e}")

# ========== 测试5: HydrostaticCanalSolver ==========
print("\n" + "-" * 80)
print("测试 5/5: HydrostaticCanalSolver (基类)")
print("-" * 80)

try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

    solver_hs = HydrostaticCanalSolver(
        length=canal_length,
        nx=51,
        B=canal_width,
        S0=0.001,
        n=0.025
    )

    solver_hs.h = np.ones(51) * initial_depth
    solver_hs.hu = np.ones(51) * initial_flow / canal_width

    initial_h_hs = np.mean(solver_hs.h)

    # 简单时间循环
    stable = True
    for step in range(n_steps):
        # 计算通量和源项
        F_mass, F_mom, S_mass, S_mom = solver_hs.compute_fluxes_and_sources(
            solver_hs.h, solver_hs.hu, solver_hs.z, solver_hs.dx
        )

        # 更新
        h_new = solver_hs.h.copy()
        hu_new = solver_hs.hu.copy()

        for i in range(solver_hs.nx):
            dh = dt * (-(F_mass[i+1] - F_mass[i])/solver_hs.dx + S_mass[i])
            dhu = dt * (-(F_mom[i+1] - F_mom[i])/solver_hs.dx + S_mom[i])

            h_new[i] = solver_hs.h[i] + dh
            hu_new[i] = solver_hs.hu[i] + dhu

            h_new[i] = max(0.0, h_new[i])

        # 边界条件
        hu_new[0] = Q_in / canal_width
        hu_new[-1] = Q_out / canal_width

        solver_hs.h = h_new
        solver_hs.hu = hu_new

        # 检查NaN
        if np.isnan(solver_hs.h).any():
            stable = False
            print(f"❌ NaN出现在第{step}步")
            break

    final_h_hs = np.mean(solver_hs.h)
    actual_dh = final_h_hs - initial_h_hs

    if stable and not np.isnan(final_h_hs):
        error = abs(actual_dh - expected_delta_h)
        error_pct = error / expected_delta_h * 100

        test_results['HydrostaticCanalSolver'] = {
            'status': 'success',
            'error_pct': error_pct,
            'error_m': error,
            'actual_dh': actual_dh,
            'stable': True
        }

        print(f"✅ 成功: 误差={error_pct:.1f}%")
    else:
        test_results['HydrostaticCanalSolver'] = {
            'status': 'unstable',
            'error': 'Numerical overflow (NaN)',
            'stable': False
        }
        print(f"❌ 数值不稳定（NaN）")

except Exception as e:
    test_results['HydrostaticCanalSolver'] = {
        'status': 'failed',
        'error': str(e),
        'stable': False
    }
    print(f"❌ 失败: {e}")

# ========== 结果汇总 ==========
print("\n" + "="*80)
print("第三步：结果汇总与建议")
print("="*80)

print("\n【精度排名】（仅包含成功的求解器）\n")

successful_solvers = [
    (name, result) for name, result in test_results.items()
    if result['status'] == 'success' and result['stable']
]

successful_solvers.sort(key=lambda x: x[1]['error_pct'])

for i, (name, result) in enumerate(successful_solvers, 1):
    stars = "⭐" * max(1, 6 - i)
    print(f"  {i}. {name:<30} {result['error_pct']:>7.1f}% {stars}")

print("\n【不稳定的求解器】（数值溢出/NaN）\n")

unstable_solvers = [
    (name, result) for name, result in test_results.items()
    if result['status'] == 'unstable'
]

for name, result in unstable_solvers:
    print(f"  ❌ {name:<30} {result.get('error', 'Unknown')}")

print("\n【失败的求解器】（异常/错误）\n")

failed_solvers = [
    (name, result) for name, result in test_results.items()
    if result['status'] == 'failed'
]

for name, result in failed_solvers:
    print(f"  ❌ {name:<30} {result.get('error', 'Unknown')}")

# ========== 删除建议 ==========
print("\n" + "="*80)
print("第四步：删除建议")
print("="*80)

print("\n【建议保留】✅\n")
for name, result in successful_solvers:
    if result['error_pct'] < 100:
        print(f"  • {name}: 误差{result['error_pct']:.1f}% - 可用于生产")

print("\n【建议删除】❌\n")

to_delete = []

# 不稳定的求解器
for name, result in unstable_solvers:
    print(f"  • {name}: 数值不稳定（NaN溢出）")
    to_delete.append(name)

# 误差>1000%的求解器
for name, result in successful_solvers:
    if result['error_pct'] > 1000:
        print(f"  • {name}: 误差{result['error_pct']:.1f}% - 实现有误")
        to_delete.append(name)

# 失败的求解器
for name, result in failed_solvers:
    print(f"  • {name}: 运行失败")
    to_delete.append(name)

print("\n" + "="*80)
print("总结")
print("="*80)

print(f"\n测试求解器总数: {len(test_results)}")
print(f"成功且稳定: {len(successful_solvers)}")
print(f"数值不稳定: {len(unstable_solvers)}")
print(f"运行失败: {len(failed_solvers)}")
print(f"建议删除: {len(to_delete)}")

if len(successful_solvers) > 0:
    best_name, best_result = successful_solvers[0]
    print(f"\n🏆 推荐求解器: {best_name}")
    print(f"   误差: {best_result['error_pct']:.1f}%")
else:
    print(f"\n⚠️  警告：没有可用的求解器！")

print("\n" + "="*80)

# 保存报告
import json
report = {
    'test_config': {
        'Q_in': Q_in,
        'Q_out': Q_out,
        'sim_time': sim_time,
        'expected_dh': expected_delta_h
    },
    'results': test_results,
    'recommendations': {
        'keep': [name for name, _ in successful_solvers if _['error_pct'] < 100],
        'delete': to_delete
    }
}

with open('solver_audit_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("✅ 详细报告已保存到: solver_audit_report.json")
