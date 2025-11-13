"""
高精度求解器测试

对比标准求解器 vs 高精度求解器的精度差异
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
try:
    # DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.single_canal_solver import SingleCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import SluiceGate

def test_three_gates_comparison():
    """测试三个闸门场景 - 对比标准vs高精度"""
    
    print("=" * 80)
    print("高精度求解器测试：三个闸门串联场景")
    print("=" * 80)
    print()
    
    # 系统参数
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    bed_slope = 0.0005
    manning_n = 0.025
    
    # 创建三个闸门（与脚本11场景1相同）
    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)
    
    print(f"系统配置:")
    print(f"  渠道长度: {canal_length}m")
    print(f"  闸门1 @ {gate1.position}m: 开度={gate1.get_opening(0)}m")
    print(f"  闸门2 @ {gate2.position}m: 开度={gate2.get_opening(0)}m (最小)")
    print(f"  闸门3 @ {gate3.position}m: 开度={gate3.get_opening(0)}m")
    print()
    
    Q_initial = 10.0
    
    # ========== 测试1: 标准求解器 ==========
    print("\n" + "=" * 80)
    print("测试1: 标准求解器")
    print("=" * 80)
    
    solver_standard = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )
    
    solver_standard.reset_with_steady_state(Q_initial)
    
    result_standard = solver_standard.solve_steady_state(
        Q_target=Q_initial,
        max_iterations=5000,
        convergence_tol=0.001,
        check_interval=500,
        verbose=True
    )
    
    # ========== 测试2: 高精度求解器 ==========
    print("\n" + "=" * 80)
    print("测试2: 高精度求解器")
    print("=" * 80)
    
    solver_hp = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )
    
    solver_hp.reset_with_steady_state(Q_initial)
    
    result_hp = solver_hp.solve_steady_state_high_precision(
        Q_target=Q_initial,
        max_iterations=50000,  # 增加迭代次数
        tol_global=1e-4,
        tol_local=1e-4,
        tol_structure=1e-4,
        tol_temporal=1e-5,
        check_interval=200,  # 降低检查频率以加快运行
        verbose=True
    )
    
    # ========== 结果对比 ==========
    print("\n" + "=" * 80)
    print("精度对比分析")
    print("=" * 80)
    
    # 计算标准求解器的详细误差
    Q_std = solver_standard.solver.Q.copy()
    Q_hp = solver_hp.solver.Q.copy()
    
    # 标准求解器的多维度误差
    Q_std_avg = np.mean(Q_std[1:-1])
    error_std_global = abs(Q_std_avg - Q_initial) / Q_initial
    
    Q_std_diff = np.abs(np.diff(Q_std))
    error_std_local = np.max(Q_std_diff) / Q_initial
    
    gate_flows_std = result_standard['gate_flows']
    error_std_structure = max([abs(gf - Q_initial) / Q_initial for gf in gate_flows_std])
    
    error_std_L2 = np.sqrt(np.mean((Q_std - Q_initial)**2)) / Q_initial
    error_std_Linf = np.max(np.abs(Q_std - Q_initial)) / Q_initial
    
    # 打印对比表
    print(f"\n{'指标':<20} {'标准求解器':<20} {'高精度求解器':<20} {'改进倍数':<15}")
    print("-" * 80)
    
    print(f"{'全局误差':<20} {error_std_global:<20.2e} {result_hp['error_global']:<20.2e} "
          f"{error_std_global/result_hp['error_global'] if result_hp['error_global'] > 0 else float('inf'):<15.1f}x")
    
    print(f"{'局部误差':<20} {error_std_local:<20.2e} {result_hp['error_local']:<20.2e} "
          f"{error_std_local/result_hp['error_local'] if result_hp['error_local'] > 0 else float('inf'):<15.1f}x")
    
    print(f"{'结构误差':<20} {error_std_structure:<20.2e} {result_hp['error_structure']:<20.2e} "
          f"{error_std_structure/result_hp['error_structure'] if result_hp['error_structure'] > 0 else float('inf'):<15.1f}x")
    
    print(f"{'L2范数':<20} {error_std_L2:<20.2e} {result_hp['error_L2']:<20.2e} "
          f"{error_std_L2/result_hp['error_L2'] if result_hp['error_L2'] > 0 else float('inf'):<15.1f}x")
    
    print(f"{'L∞范数':<20} {error_std_Linf:<20.2e} {result_hp['error_Linf']:<20.2e} "
          f"{error_std_Linf/result_hp['error_Linf'] if result_hp['error_Linf'] > 0 else float('inf'):<15.1f}x")
    
    print(f"\n{'迭代次数':<20} {result_standard['iterations']:<20} {result_hp['iterations']:<20} "
          f"{result_hp['iterations']/result_standard['iterations']:<15.2f}x")
    
    print(f"{'仿真时间':<20} {result_standard['final_time']:<20.0f}s {result_hp['final_time']:<20.0f}s "
          f"{result_hp['final_time']/result_standard['final_time']:<15.2f}x")
    
    # 目标达成度
    print(f"\n{'='*80}")
    print(f"精度提升目标评估")
    print(f"{'='*80}")
    
    target_error = 1e-4
    
    print(f"\n目标：所有误差 < {target_error:.0e} (0.01%)")
    print(f"\n高精度求解器结果:")
    print(f"  全局误差: {result_hp['error_global']:.2e} {'' if result_hp['error_global'] < target_error else ''}")
    print(f"  局部误差: {result_hp['error_local']:.2e} {'' if result_hp['error_local'] < target_error else ''}")
    print(f"  结构误差: {result_hp['error_structure']:.2e} {'' if result_hp['error_structure'] < target_error else ''}")
    print(f"  时间误差: {result_hp['error_temporal']:.2e} {'' if result_hp['error_temporal'] < target_error else ''}")
    
    all_passed = (result_hp['error_global'] < target_error and
                  result_hp['error_local'] < target_error and
                  result_hp['error_structure'] < target_error and
                  result_hp['error_temporal'] < target_error)
    
    print(f"\n{'='*80}")
    if all_passed:
        print(f" 成功达到10^-4精度目标！")
    else:
        print(f" 未完全达到目标，需要进一步优化 ")
    print(f"{'='*80}")
    
    return all_passed

if __name__ == '__main__':
    success = test_three_gates_comparison()
    sys.exit(0 if success else 1)
