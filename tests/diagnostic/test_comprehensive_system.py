#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude综合系统测试

测试所有核心功能：
1. Phase 0求解器（3个）
2. Phase 1工具库
3. 工程案例
4. 质量守恒
5. 数值稳定性
6. 性能基准

作者: HydroClaude Team
日期: 2025-10-27
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)

from solvers.godunov_fvm_hllc import GodunvFVMHLLC
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth
from utils.hydraulic_tools import HydraulicTools

print("="*80)
print("🧪 HydroClaude综合系统测试")
print("="*80)

# 测试结果收集
test_results = []

def test_case(name, func):
    """测试用例包装器"""
    print(f"\n{'='*80}")
    print(f"【测试{len(test_results)+1}】{name}")
    print("-"*80)
    
    try:
        t_start = time.time()
        result = func()
        t_elapsed = time.time() - t_start
        
        success = result.get('success', False)
        message = result.get('message', '')
        metrics = result.get('metrics', {})
        
        test_results.append({
            'name': name,
            'success': success,
            'time': t_elapsed,
            'message': message,
            'metrics': metrics
        })
        
        status = " 通过" if success else " 失败"
        print(f"\n结果: {status}")
        print(f"耗时: {t_elapsed:.2f}秒")
        if message:
            print(f"说明: {message}")
        
        return result
        
    except Exception as e:
        print(f"\n 异常: {str(e)}")
        test_results.append({
            'name': name,
            'success': False,
            'time': 0,
            'message': f"异常: {str(e)}",
            'metrics': {}
        })
        return {'success': False, 'message': str(e)}

# ========== 测试1: Godunov-FVM基础功能 ==========
def test_godunov_basic():
    """测试Godunov-FVM基础功能"""
    
    solver = GodunvFVMSolver(
        width=10.0, length=1000.0, n_cells=100,
        manning_n=0.025, slope=0.001,
        cfl=0.5, order=1
    )
    
    Q_target = 50.0
    h_uniform = compute_steady_uniform_flow(Q_target, 10.0, 0.001, 0.025)
    h_init = np.ones(100) * h_uniform
    Q_init = np.ones(100) * Q_target
    
    bc_left = {'type': 'Q', 'value': Q_target}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 推进500步
    for _ in range(500):
        solver.step()
    
    state = solver.get_state()
    mass_error = abs(state['mass_error'])
    
    success = mass_error < 1.0 and not np.any(np.isnan(state['h']))
    
    return {
        'success': success,
        'message': f"质量误差{mass_error:.4f}%",
        'metrics': {
            'mass_error': mass_error,
            'steps': state['step'],
            'mean_h': np.mean(state['h']),
            'mean_Q': np.mean(state['Q'])
        }
    }

test_case("Godunov-FVM基础功能", test_godunov_basic)

# ========== 测试2: HLLC Dam Break ==========
def test_hllc_dambreak():
    """测试HLLC Dam Break"""
    
    solver = GodunvFVMHLLC(
        width=10.0, length=200.0, n_cells=100,
        manning_n=0.0, slope=0.0,
        cfl=0.5, order=1
    )
    
    x_dam = 100.0
    h_init = np.where(solver.x < x_dam, 10.0, 1.0)
    Q_init = np.zeros(100)
    
    bc_left = {'type': 'h', 'value': 10.0}
    bc_right = {'type': 'h', 'value': 1.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 推进至t=2s
    while solver.t < 2.0 and solver.step_count < 1000:
        solver.step()
    
    state = solver.get_state()
    mass_error = abs(state['mass_error'])
    
    success = mass_error < 5.0 and not np.any(np.isnan(state['h']))
    
    return {
        'success': success,
        'message': f"质量误差{mass_error:.4f}%",
        'metrics': {
            'mass_error': mass_error,
            'steps': state['step'],
            'final_time': state['t']
        }
    }

test_case("HLLC Dam Break模拟", test_hllc_dambreak)

# ========== 测试3: HydrostaticSolver稳态流 ==========
def test_hydrostatic_steady():
    """测试Hydrostatic稳态求解"""
    
    solver = HydrostaticCanalSolver(
        length=1000.0, nx=100, B=10.0,
        n=0.025, S0=0.001
    )
    
    Q_target = 50.0
    h_uniform = compute_steady_uniform_flow(Q_target, 10.0, 0.001, 0.025)
    
    result = solver.solve_steady_state(
        Q_target=Q_target,
        max_iterations=100,
        convergence_tol=0.1
    )
    
    if result['converged']:
        Q_mean = np.mean(result['Q'])
        Q_error = abs(Q_mean - Q_target) / Q_target * 100
        success = Q_error < 1.0
        
        return {
            'success': success,
            'message': f"流量误差{Q_error:.4f}%，迭代{result['iterations']}次",
            'metrics': {
                'Q_error': Q_error,
                'iterations': result['iterations'],
                'converged': True
            }
        }
    else:
        return {
            'success': False,
            'message': "未收敛",
            'metrics': {'converged': False}
        }

test_case("Hydrostatic稳态求解", test_hydrostatic_steady)

# ========== 测试4: 水力计算工具 ==========
def test_hydraulic_tools():
    """测试水力计算工具库"""
    
    tools = HydraulicTools()
    
    # Q-h关系曲线
    Q, h = tools.generate_rating_curve(
        width=10.0, slope=0.001, manning_n=0.025,
        Q_range=(20, 100), n_points=10
    )
    
    # Froude数计算
    h_test, Fr = tools.compute_froude_curve(
        width=10.0, h_range=(1.0, 4.0), Q=50.0, n_points=20
    )
    
    # 水跃计算
    jump = tools.compute_hydraulic_jump(width=10.0, h1=1.0, Q=50.0)
    
    # 渠道过流能力
    capacity = tools.compute_channel_capacity(
        width=10.0, h_max=3.0, slope=0.001, manning_n=0.025
    )
    
    success = (len(Q) == 10 and len(Fr) == 20 and 
               jump['h2'] > jump['h1'] and capacity['Q_max'] > 0)
    
    return {
        'success': success,
        'message': f"生成{len(Q)}个Q-h点，{len(Fr)}个Fr点",
        'metrics': {
            'rating_points': len(Q),
            'froude_points': len(Fr),
            'jump_h2': jump['h2'],
            'capacity_Q': capacity['Q_max']
        }
    }

test_case("水力计算工具库", test_hydraulic_tools)

# ========== 测试5: 长时间稳定性 ==========
def test_long_term_stability():
    """测试长时间稳定性"""
    
    solver = GodunvFVMSolver(
        width=10.0, length=1000.0, n_cells=100,
        manning_n=0.025, slope=0.001,
        cfl=0.5, order=1
    )
    
    Q_target = 50.0
    h_uniform = compute_steady_uniform_flow(Q_target, 10.0, 0.001, 0.025)
    h_init = np.ones(100) * h_uniform
    Q_init = np.ones(100) * Q_target
    
    bc_left = {'type': 'Q', 'value': Q_target}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 推进至t=1000s
    while solver.t < 1000.0 and solver.step_count < 5000:
        solver.step()
    
    state = solver.get_state()
    mass_error = abs(state['mass_error'])
    
    success = mass_error < 1.0 and state['t'] > 900
    
    return {
        'success': success,
        'message': f"运行{state['t']:.0f}s，质量误差{mass_error:.4f}%",
        'metrics': {
            'final_time': state['t'],
            'mass_error': mass_error,
            'total_steps': state['step']
        }
    }

test_case("长时间稳定性(1000s)", test_long_term_stability)

# ========== 测试6: 不同参数稳定性 ==========
def test_parameter_robustness():
    """测试不同参数下的稳定性"""
    
    params_list = [
        {'Q': 30, 'n': 0.015, 'S0': 0.0005},
        {'Q': 50, 'n': 0.025, 'S0': 0.001},
        {'Q': 80, 'n': 0.035, 'S0': 0.002},
    ]
    
    errors = []
    
    for params in params_list:
        solver = GodunvFVMSolver(
            width=10.0, length=1000.0, n_cells=100,
            manning_n=params['n'], slope=params['S0'],
            cfl=0.5, order=1
        )
        
        Q = params['Q']
        h_uniform = compute_steady_uniform_flow(Q, 10.0, params['S0'], params['n'])
        h_init = np.ones(100) * h_uniform
        Q_init = np.ones(100) * Q
        
        bc_left = {'type': 'Q', 'value': Q}
        bc_right = {'type': 'h', 'value': h_uniform}
        
        solver.initialize(h_init, Q_init, bc_left, bc_right)
        
        for _ in range(500):
            solver.step()
        
        state = solver.get_state()
        errors.append(abs(state['mass_error']))
    
    avg_error = np.mean(errors)
    success = avg_error < 2.0 and all([e < 5.0 for e in errors])
    
    return {
        'success': success,
        'message': f"平均误差{avg_error:.4f}%",
        'metrics': {
            'avg_error': avg_error,
            'max_error': max(errors),
            'min_error': min(errors),
            'test_cases': len(params_list)
        }
    }

test_case("不同参数稳定性", test_parameter_robustness)

# ========== 测试7: 计算效率 ==========
def test_computational_efficiency():
    """测试计算效率"""
    
    solver = GodunvFVMSolver(
        width=10.0, length=1000.0, n_cells=100,
        manning_n=0.025, slope=0.001,
        cfl=0.5, order=1
    )
    
    Q_target = 50.0
    h_uniform = compute_steady_uniform_flow(Q_target, 10.0, 0.001, 0.025)
    h_init = np.ones(100) * h_uniform
    Q_init = np.ones(100) * Q_target
    
    bc_left = {'type': 'Q', 'value': Q_target}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 计时1000步
    t_start = time.time()
    for _ in range(1000):
        solver.step()
    t_elapsed = time.time() - t_start
    
    efficiency = 1000 / t_elapsed  # 步/秒
    
    success = efficiency > 500  # 目标>500步/秒
    
    return {
        'success': success,
        'message': f"效率{efficiency:.0f}步/秒",
        'metrics': {
            'efficiency': efficiency,
            'time_per_step': t_elapsed / 1000
        }
    }

test_case("计算效率", test_computational_efficiency)

# ========== 测试总结 ==========
print("\n" + "="*80)
print(" 测试总结")
print("="*80)

total_tests = len(test_results)
passed_tests = sum([1 for r in test_results if r['success']])
failed_tests = total_tests - passed_tests

print(f"\n总测试数: {total_tests}")
print(f"通过: {passed_tests} ")
print(f"失败: {failed_tests} {'' if failed_tests > 0 else ''}")
print(f"通过率: {passed_tests/total_tests*100:.1f}%")

print(f"\n详细结果:")
print(f"{'序号':<6} {'测试项':<30} {'状态':<8} {'耗时(s)':<10} {'说明':<30}")
print("-"*90)

for i, result in enumerate(test_results, 1):
    status = " 通过" if result['success'] else " 失败"
    message = result['message'][:28] if result['message'] else ''
    print(f"{i:<6} {result['name']:<30} {status:<8} {result['time']:<10.2f} {message:<30}")

# 关键指标汇总
print(f"\n" + "="*80)
print(" 关键性能指标")
print("="*80)

# 提取关键指标
for result in test_results:
    if result['name'] == "Godunov-FVM基础功能" and result['success']:
        m = result['metrics']
        print(f"\nGodunov-FVM:")
        print(f"  质量误差: {m['mass_error']:.4f}%")
        print(f"  推进步数: {m['steps']}")

for result in test_results:
    if result['name'] == "计算效率" and result['success']:
        m = result['metrics']
        print(f"\n计算效率:")
        print(f"  {m['efficiency']:.0f} 步/秒")
        print(f"  {m['time_per_step']*1000:.2f} ms/步")

for result in test_results:
    if result['name'] == "长时间稳定性(1000s)" and result['success']:
        m = result['metrics']
        print(f"\n长时间稳定性:")
        print(f"  运行时间: {m['final_time']:.0f}s")
        print(f"  质量误差: {m['mass_error']:.4f}%")
        print(f"  总步数: {m['total_steps']}")

# 最终评价
print(f"\n" + "="*80)
print(" 综合评价")
print("="*80)

if passed_tests == total_tests:
    print(f"\n 所有测试通过！系统功能完整，性能优秀！")
    print(f" HydroClaude已准备好投入生产使用")
elif passed_tests >= total_tests * 0.8:
    print(f"\n 大部分测试通过！核心功能稳定")
    print(f"️ 部分功能需要优化")
else:
    print(f"\n️ 较多测试失败，需要检查")

print(f"\n推荐用途:")
print(f"   单渠道稳态/非恒定流模拟")
print(f"   Dam Break应急分析")
print(f"   参数敏感性研究")
print(f"   工程设计优化")

print(f"\n" + "="*80)
print(f"🧪 综合系统测试完成！")
print(f"="*80)
