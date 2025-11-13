#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实际工况综合测试

测试HydrostaticCanalSolver在实际水利工程场景下的性能
"""

import sys
sys.path.insert(0, '/workspace')

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import quick_validate_steady_state


def test_case_1_single_gate():
    """
    案例1：单闸门调控（最常见工况）
    
    场景：灌溉渠道，用闸门调节下游水位
    """
    print("\n" + "="*80)
    print("案例1：单闸门灌溉渠道")
    print("="*80)
    
    # 参数（典型灌溉渠道）
    L = 5000.0  # 5km渠道
    Q = 50.0    # 50 m^3/s
    B = 15.0    # 15m宽
    S0 = 0.0005 # 0.05%坡度
    n = 0.025
    
    # 闸门位置和开度
    gate_pos = 2500.0
    gate_opening = 3.0  # 3m开度
    
    # 创建求解器
    gate = SluiceGate(position=gate_pos, width=B, opening=gate_opening)
    solver = HydrostaticCanalSolver(
        length=L, nx=201, B=B, S0=S0, n=n,
        internal_structures=[(gate_pos, gate)]
    )
    
    # 边界条件
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    h_downstream = h_uniform * 1.5  # 下游壅水
    
    print(f"\n参数设置:")
    print(f"  渠道: L={L/1000:.1f}km, B={B}m, S0={S0*100:.2f}%, n={n}")
    print(f"  流量: Q={Q} m^3/s")
    print(f"  闸门: 位置={gate_pos/1000:.1f}km, 开度={gate_opening}m")
    print(f"  均匀流水深: {h_uniform:.3f}m")
    print(f"  下游水深: {h_downstream:.3f}m")
    
    # 稳态求解
    print(f"\n开始求解...")
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_downstream,
        max_iterations=100,
        convergence_tol=0.1
    )
    
    # 验证
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="单闸门灌溉渠道"
    )
    
    # 分析水位变化
    x_gate_idx = np.argmin(np.abs(solver.x - gate_pos))
    h_upstream = solver.h[x_gate_idx - 10]
    h_downstream_actual = solver.h[x_gate_idx + 10]
    water_level_drop = h_upstream - h_downstream_actual
    
    print(f"\n水力特性:")
    print(f"  闸前水深: {h_upstream:.3f}m")
    print(f"  闸后水深: {h_downstream_actual:.3f}m")
    print(f"  水位跌落: {water_level_drop:.3f}m")
    print(f"  能量损失: {water_level_drop * 9.81 * 1000:.1f} kW (假设ρ=1000 kg/m^3)")
    
    return {
        'solver': solver,
        'result': result,
        'validator': validator,
        'case_name': '单闸门灌溉渠道'
    }


def test_case_2_cascade_gates():
    """
    案例2：梯级闸门（复杂工况）
    
    场景：城市排水系统，多级闸门调控
    """
    print("\n" + "="*80)
    print("案例2：三级梯级闸门系统")
    print("="*80)
    
    # 参数
    L = 3000.0
    Q = 30.0
    B = 10.0
    S0 = 0.001
    n = 0.020
    
    # 三个闸门
    gate1 = SluiceGate(position=1000.0, width=B, opening=2.5)
    gate2 = SluiceGate(position=1500.0, width=B, opening=2.0)
    gate3 = SluiceGate(position=2000.0, width=B, opening=2.5)
    
    solver = HydrostaticCanalSolver(
        length=L, nx=301, B=B, S0=S0, n=n,
        internal_structures=[
            (1000.0, gate1),
            (1500.0, gate2),
            (2000.0, gate3)
        ]
    )
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    h_downstream = h_uniform * 1.3
    
    print(f"\n参数设置:")
    print(f"  渠道: L={L/1000:.1f}km, B={B}m, Q={Q} m^3/s")
    print(f"  闸门1: 位置={1000.0}m, 开度={2.5}m")
    print(f"  闸门2: 位置={1500.0}m, 开度={2.0}m")
    print(f"  闸门3: 位置={2000.0}m, 开度={2.5}m")
    
    print(f"\n开始求解...")
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_downstream,
        max_iterations=150,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="三级梯级闸门"
    )
    
    # 分析每个闸门的水位跌落
    gate_positions = [1000.0, 1500.0, 2000.0]
    print(f"\n各级闸门水力特性:")
    for i, pos in enumerate(gate_positions):
        idx = np.argmin(np.abs(solver.x - pos))
        h_before = solver.h[idx - 5]
        h_after = solver.h[idx + 5]
        drop = h_before - h_after
        print(f"  闸门{i+1}: 水位跌落={drop:.3f}m")
    
    return {
        'solver': solver,
        'result': result,
        'validator': validator,
        'case_name': '三级梯级闸门'
    }


def test_case_3_mild_slope():
    """
    案例3：缓坡渠道（M1壅水曲线）
    
    场景：大型输水渠道，缓变流
    """
    print("\n" + "="*80)
    print("案例3：缓坡渠道壅水曲线")
    print("="*80)
    
    # 参数（大型输水渠）
    L = 10000.0  # 10km
    Q = 200.0    # 200 m^3/s
    B = 30.0     # 30m宽
    S0 = 0.0002  # 0.02%缓坡
    n = 0.020
    
    solver = HydrostaticCanalSolver(
        length=L, nx=401, B=B, S0=S0, n=n
    )
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    h_downstream = h_uniform * 2.0  # 下游控制产生M1曲线
    
    print(f"\n参数设置:")
    print(f"  渠道: L={L/1000:.0f}km, B={B}m, S0={S0*100:.3f}%")
    print(f"  流量: Q={Q} m^3/s")
    print(f"  均匀流水深: {h_uniform:.3f}m")
    print(f"  下游水深: {h_downstream:.3f}m (产生M1壅水曲线)")
    
    print(f"\n开始求解...")
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_downstream,
        max_iterations=100,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="缓坡壅水曲线"
    )
    
    # 分析壅水范围
    tolerance = h_uniform * 0.05  # 5%容差
    affected_indices = np.where(solver.h > h_uniform + tolerance)[0]
    if len(affected_indices) > 0:
        backwater_length = L - solver.x[affected_indices[0]]
        print(f"\n壅水特性:")
        print(f"  壅水影响范围: {backwater_length/1000:.2f}km")
        print(f"  壅水比 L_b/L: {backwater_length/L*100:.1f}%")
    
    return {
        'solver': solver,
        'result': result,
        'validator': validator,
        'case_name': '缓坡壅水曲线'
    }


def test_case_4_steep_slope():
    """
    案例4：陡坡渠道（急流）
    
    场景：山区渠道，超临界流动
    """
    print("\n" + "="*80)
    print("案例4：陡坡渠道急流")
    print("="*80)
    
    # 参数
    L = 2000.0
    Q = 40.0
    B = 8.0
    S0 = 0.01    # 1%陡坡
    n = 0.015
    
    solver = HydrostaticCanalSolver(
        length=L, nx=201, B=B, S0=S0, n=n
    )
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    
    # 陡坡：上游控制
    h_downstream = h_uniform * 0.8
    
    print(f"\n参数设置:")
    print(f"  渠道: L={L/1000:.1f}km, B={B}m, S0={S0*100:.1f}% (陡坡)")
    print(f"  流量: Q={Q} m^3/s")
    print(f"  均匀流水深: {h_uniform:.3f}m")
    
    # 计算Froude数
    v_uniform = Q / (B * h_uniform)
    Fr = v_uniform / np.sqrt(9.81 * h_uniform)
    print(f"  均匀流Froude数: {Fr:.2f} ({'超临界' if Fr > 1 else '亚临界'})")
    
    print(f"\n开始求解...")
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_downstream,
        max_iterations=100,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="陡坡急流"
    )
    
    return {
        'solver': solver,
        'result': result,
        'validator': validator,
        'case_name': '陡坡急流'
    }


def test_case_5_large_scale():
    """
    案例5：大型调水工程
    
    场景：长距离调水，多种水工建筑物
    """
    print("\n" + "="*80)
    print("案例5：大型调水工程")
    print("="*80)
    
    # 参数（南水北调级别）
    L = 50000.0   # 50km
    Q = 500.0     # 500 m^3/s
    B = 50.0      # 50m宽
    S0 = 0.0001   # 0.01%
    n = 0.018
    
    # 多个控制闸门
    gate1 = SluiceGate(position=10000.0, width=B, opening=8.0)
    gate2 = SluiceGate(position=25000.0, width=B, opening=7.5)
    gate3 = SluiceGate(position=40000.0, width=B, opening=8.0)
    
    solver = HydrostaticCanalSolver(
        length=L, nx=501, B=B, S0=S0, n=n,
        internal_structures=[
            (10000.0, gate1),
            (25000.0, gate2),
            (40000.0, gate3)
        ]
    )
    
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    h_downstream = h_uniform * 1.2
    
    print(f"\n参数设置:")
    print(f"  渠道长度: {L/1000:.0f}km")
    print(f"  设计流量: {Q} m^3/s")
    print(f"  渠道宽度: {B}m")
    print(f"  控制闸门: 3座 (位于10km, 25km, 40km)")
    
    print(f"\n开始求解...")
    result = solver.solve_steady_state(
        Q_target=Q,
        h_downstream=h_downstream,
        max_iterations=200,
        convergence_tol=0.1
    )
    
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q,
        name="大型调水工程"
    )
    
    # 分析水位变化
    h_min = np.min(solver.h)
    h_max = np.max(solver.h)
    h_range = h_max - h_min
    
    print(f"\n水位统计:")
    print(f"  最小水深: {h_min:.3f}m")
    print(f"  最大水深: {h_max:.3f}m")
    print(f"  水位变幅: {h_range:.3f}m")
    
    return {
        'solver': solver,
        'result': result,
        'validator': validator,
        'case_name': '大型调水工程'
    }


def generate_summary_report(all_results):
    """生成综合报告"""
    print("\n" + "="*80)
    print("综合测试报告")
    print("="*80)
    
    print(f"\n{'案例':<20} {'流量误差':<12} {'迭代次数':<10} {'收敛时间':<12} {'状态'}")
    print("-"*80)
    
    for res in all_results:
        validator = res['validator']
        result = res['result']
        case_name = res['case_name']
        
        # 提取关键指标
        flow_result = validator.results.get('flow_conservation', {})
        flow_error = flow_result.get('error_percent', 0.0)
        n_iter = result.get('iterations', 'N/A')
        converged = result.get('converged', False)
        time = result.get('solve_time', 0.0)
        
        status = " 成功" if converged else " 失败"
        
        print(f"{case_name:<20} {flow_error:>10.6f}% {n_iter:>9} {time:>10.3f}s {status}")
    
    # 统计
    n_success = sum(1 for res in all_results if res['result'].get('converged', False))
    success_rate = n_success / len(all_results) * 100
    
    avg_flow_error = np.mean([res['validator'].results.get('flow_conservation', {}).get('error_percent', 0.0) for res in all_results])
    max_flow_error = np.max([res['validator'].results.get('flow_conservation', {}).get('error_percent', 0.0) for res in all_results])
    
    print(f"\n总体统计:")
    print(f"  测试案例数: {len(all_results)}")
    print(f"  成功案例数: {n_success}")
    print(f"  成功率: {success_rate:.1f}%")
    print(f"  平均流量误差: {avg_flow_error:.6f}%")
    print(f"  最大流量误差: {max_flow_error:.6f}%")
    
    # 性能评级
    print(f"\n性能评级:")
    if success_rate == 100 and max_flow_error < 0.01:
        print(f"  ⭐⭐⭐⭐⭐ 世界一流！")
    elif success_rate >= 80 and max_flow_error < 0.1:
        print(f"  ⭐⭐⭐⭐ 优秀")
    elif success_rate >= 60 and max_flow_error < 1.0:
        print(f"  ⭐⭐⭐ 良好")
    else:
        print(f"  需要改进")


def plot_all_cases(all_results):
    """绘制所有案例的水面线"""
    n_cases = len(all_results)
    fig, axes = plt.subplots(n_cases, 1, figsize=(14, 4*n_cases))
    
    if n_cases == 1:
        axes = [axes]
    
    for i, res in enumerate(all_results):
        ax = axes[i]
        solver = res['solver']
        case_name = res['case_name']
        
        # 水面线
        ax.plot(solver.x/1000, solver.h, 'b-', linewidth=2, label='水深')
        
        # 河底线
        z_bottom = -solver.z
        ax.plot(solver.x/1000, z_bottom, 'k-', linewidth=1, label='河底')
        
        # 水面线
        water_surface = solver.h + z_bottom
        ax.fill_between(solver.x/1000, z_bottom, water_surface, 
                        alpha=0.3, color='cyan', label='水体')
        
        # 标注闸门位置
        if solver.internal_structures:
            for pos, _ in solver.internal_structures:
                ax.axvline(pos/1000, color='red', linestyle='--', 
                          alpha=0.7, linewidth=1.5)
        
        ax.set_xlabel('距离 (km)', fontsize=11)
        ax.set_ylabel('高程 (m)', fontsize=11)
        ax.set_title(f'{case_name} - 纵断面', fontsize=12, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fig_path = f'/workspace/validation_cases/results/realistic_cases_{timestamp}.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n 图表已保存: {fig_path}")
    plt.close()


def main():
    """主函数"""
    print("="*80)
    print("实际工况综合测试")
    print("="*80)
    print("\n测试HydrostaticCanalSolver在实际水利工程场景下的性能")
    print("包括：灌溉渠道、梯级闸门、壅水曲线、急流、大型调水工程")
    
    all_results = []
    
    # 运行所有测试
    try:
        result1 = test_case_1_single_gate()
        all_results.append(result1)
    except Exception as e:
        print(f" 案例1失败: {e}")
    
    try:
        result2 = test_case_2_cascade_gates()
        all_results.append(result2)
    except Exception as e:
        print(f" 案例2失败: {e}")
    
    try:
        result3 = test_case_3_mild_slope()
        all_results.append(result3)
    except Exception as e:
        print(f" 案例3失败: {e}")
    
    try:
        result4 = test_case_4_steep_slope()
        all_results.append(result4)
    except Exception as e:
        print(f" 案例4失败: {e}")
    
    try:
        result5 = test_case_5_large_scale()
        all_results.append(result5)
    except Exception as e:
        print(f" 案例5失败: {e}")
    
    # 生成报告
    if all_results:
        generate_summary_report(all_results)
        plot_all_cases(all_results)
    
    print("\n" + "="*80)
    print("测试完成！")
    print("="*80)


if __name__ == '__main__':
    main()
