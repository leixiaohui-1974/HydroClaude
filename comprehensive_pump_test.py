#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串联闸泵群全面工况测试

测试场景：
1. 稳态 - 不同流量
2. 泵站启动
3. 泵站关闭
4. 流量阶跃变化
5. 多泵站系统
6. 闸泵联合调控
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import PumpStation, SluiceGate

def test_case_1_steady_different_flows():
    """测试1: 稳态 - 不同流量下的泵站扬程"""
    print("\n" + "=" * 80)
    print("测试1: 稳态 - 不同流量（10, 30, 50, 70 m³/s）")
    print("=" * 80)
    
    results = []
    flows = [10.0, 30.0, 50.0, 70.0]
    
    for Q in flows:
        # 创建系统
        pump = PumpStation(position=25000.0, width=10.0, rated_flow=100.0, 
                          rated_head=5.0, min_suction_head=2.0)
        pump.is_running = True
        
        solver = HydrostaticCanalSolver(
            length=50000.0, nx=251, B=10.0, S0=0.0, n=0.025, eps_dry=0.01,
            internal_structures=[(25000.0, pump)]
        )
        
        # 稳态求解
        result = solver.solve_steady_state(
            Q_target=Q, h_downstream=3.0, max_iterations=1000,
            convergence_tol=0.001, dt=0.5, verbose=False
        )
        
        # 验证扬程
        pump_idx = np.argmin(np.abs(solver.x - 25000.0))
        h_up = solver.h[pump_idx - 1]
        h_down = solver.h[pump_idx + 1]
        actual_head = h_down - h_up
        precision = actual_head / 5.0 * 100
        
        results.append({
            'Q': Q,
            'h_up': h_up,
            'h_down': h_down,
            'actual_head': actual_head,
            'precision': precision
        })
        
        status = "" if 95 <= precision <= 105 else ""
        print(f"  Q={Q:5.1f} m³/s: 扬程={actual_head:.4f}m, 精度={precision:6.2f}% {status}")
    
    # 判断
    all_passed = all(95 <= r['precision'] <= 105 for r in results)
    print(f"\n结果: {' 全部通过' if all_passed else ' 部分失败'}")
    return all_passed


def test_case_2_pump_startup():
    """测试2: 泵站启动"""
    print("\n" + "=" * 80)
    print("测试2: 非恒定流 - 泵站启动（t=0关闭，t=5s启动）")
    print("=" * 80)
    
    pump = PumpStation(position=25000.0, width=10.0, rated_flow=50.0,
                      rated_head=5.0, min_suction_head=2.0)
    pump.is_running = False  # 初始关闭
    
    solver = HydrostaticCanalSolver(
        length=50000.0, nx=251, B=10.0, S0=0.0, n=0.025, eps_dry=0.01,
        internal_structures=[(25000.0, pump)]
    )
    
    # 稳态求解（泵站关闭）
    solver.solve_steady_state(Q_target=50.0, h_downstream=3.0, 
                             max_iterations=500, verbose=False)
    
    pump_idx = np.argmin(np.abs(solver.x - 25000.0))
    h_initial = solver.h[pump_idx + 1]
    
    # 启动泵站
    pump.is_running = True
    
    # 非恒定流
    result = solver.solve_transient_adaptive(
        t_end=20.0, dt_initial=0.5, dt_max=0.5,
        Q_upstream=50.0, h_downstream=3.0,
        save_interval_time=2.0, verbose=False
    )
    
    h_final = solver.h[pump_idx + 1]
    delta_h = h_final - h_initial
    
    print(f"  初始下游水深（泵站关）: {h_initial:.4f} m")
    print(f"  最终下游水深（泵站开）: {h_final:.4f} m")
    print(f"  水深上升: {delta_h:.4f} m")
    print(f"  预期上升: ~5.0 m")
    
    # 判断：泵站启动后水深应上升
    passed = delta_h > 2.0  # 至少上升2m
    print(f"\n结果: {' 通过' if passed else ' 失败'} (水深上升 {delta_h:.2f}m)")
    return passed


def test_case_3_pump_shutdown():
    """测试3: 泵站关闭"""
    print("\n" + "=" * 80)
    print("测试3: 非恒定流 - 泵站关闭（t=0运行，t=5s关闭）")
    print("=" * 80)
    
    pump = PumpStation(position=25000.0, width=10.0, rated_flow=50.0,
                      rated_head=5.0, min_suction_head=2.0)
    pump.is_running = True
    
    solver = HydrostaticCanalSolver(
        length=50000.0, nx=251, B=10.0, S0=0.0, n=0.025, eps_dry=0.01,
        internal_structures=[(25000.0, pump)]
    )
    
    # 稳态（泵站运行）
    solver.solve_steady_state(Q_target=50.0, h_downstream=3.0,
                             max_iterations=1000, verbose=False)
    
    pump_idx = np.argmin(np.abs(solver.x - 25000.0))
    h_initial = solver.h[pump_idx + 1]
    
    # 关闭泵站
    pump.is_running = False
    
    # 非恒定流
    result = solver.solve_transient_adaptive(
        t_end=20.0, dt_initial=0.5, dt_max=0.5,
        Q_upstream=50.0, h_downstream=3.0,
        save_interval_time=2.0, verbose=False
    )
    
    h_final = solver.h[pump_idx + 1]
    delta_h = h_initial - h_final
    
    print(f"  初始下游水深（泵站开）: {h_initial:.4f} m")
    print(f"  最终下游水深（泵站关）: {h_final:.4f} m")
    print(f"  水深下降: {delta_h:.4f} m")
    
    passed = delta_h > 2.0
    print(f"\n结果: {' 通过' if passed else ' 失败'} (水深下降 {delta_h:.2f}m)")
    return passed


def test_case_4_flow_step_change():
    """测试4: 流量阶跃变化"""
    print("\n" + "=" * 80)
    print("测试4: 非恒定流 - 上游流量阶跃（30→70 m³/s）")
    print("=" * 80)
    
    pump = PumpStation(position=25000.0, width=10.0, rated_flow=100.0,
                      rated_head=5.0, min_suction_head=2.0)
    pump.is_running = True
    
    solver = HydrostaticCanalSolver(
        length=50000.0, nx=251, B=10.0, S0=0.0, n=0.025, eps_dry=0.01,
        internal_structures=[(25000.0, pump)]
    )
    
    # 稳态（Q=30）
    solver.solve_steady_state(Q_target=30.0, h_downstream=3.0,
                             max_iterations=1000, verbose=False)
    
    pump_idx = np.argmin(np.abs(solver.x - 25000.0))
    head_initial = solver.h[pump_idx + 1] - solver.h[pump_idx - 1]
    
    # 流量阶跃到70
    result = solver.solve_transient_adaptive(
        t_end=30.0, dt_initial=0.5, dt_max=0.5,
        Q_upstream=70.0, h_downstream=3.0,
        save_interval_time=5.0, verbose=False
    )
    
    head_final = solver.h[pump_idx + 1] - solver.h[pump_idx - 1]
    
    print(f"  初始扬程（Q=30）: {head_initial:.4f} m")
    print(f"  最终扬程（Q=70）: {head_final:.4f} m")
    print(f"  额定扬程: 5.000 m")
    
    # 扬程应保持在95-105%范围
    precision_initial = head_initial / 5.0 * 100
    precision_final = head_final / 5.0 * 100
    
    passed = (90 <= precision_initial <= 110) and (90 <= precision_final <= 110)
    print(f"\n结果: {' 通过' if passed else ' 失败'}")
    print(f"  初始精度: {precision_initial:.1f}%")
    print(f"  最终精度: {precision_final:.1f}%")
    return passed


def test_case_5_two_pumps():
    """测试5: 双泵站系统"""
    print("\n" + "=" * 80)
    print("测试5: 稳态 - 双泵站系统（25km和75km）")
    print("=" * 80)
    
    pump1 = PumpStation(position=25000.0, width=10.0, rated_flow=50.0,
                       rated_head=3.0, min_suction_head=2.0)
    pump1.is_running = True
    
    pump2 = PumpStation(position=75000.0, width=10.0, rated_flow=50.0,
                       rated_head=4.0, min_suction_head=2.0)
    pump2.is_running = True
    
    solver = HydrostaticCanalSolver(
        length=100000.0, nx=501, B=10.0, S0=0.0, n=0.025, eps_dry=0.01,
        internal_structures=[(25000.0, pump1), (75000.0, pump2)]
    )
    
    # 稳态求解
    solver.solve_steady_state(Q_target=30.0, h_downstream=3.0,
                             max_iterations=2000, verbose=False)
    
    # 验证两个泵站
    results = []
    for pump_pos, rated_head in [(25000.0, 3.0), (75000.0, 4.0)]:
        idx = np.argmin(np.abs(solver.x - pump_pos))
        h_up = solver.h[idx - 1]
        h_down = solver.h[idx + 1]
        actual_head = h_down - h_up
        precision = actual_head / rated_head * 100
        results.append({
            'position': pump_pos/1000,
            'actual': actual_head,
            'rated': rated_head,
            'precision': precision
        })
        
        status = "" if 90 <= precision <= 110 else ""
        print(f"  泵站{pump_pos/1000:.0f}km: 扬程={actual_head:.4f}m (额定{rated_head}m), "
              f"精度={precision:.1f}% {status}")
    
    passed = all(90 <= r['precision'] <= 110 for r in results)
    print(f"\n结果: {' 全部通过' if passed else ' 部分失败'}")
    return passed


def test_case_6_gate_pump_interaction():
    """测试6: 闸泵联合调控"""
    print("\n" + "=" * 80)
    print("测试6: 稳态 - 闸门+泵站联合系统")
    print("=" * 80)
    
    gate = SluiceGate(position=15000.0, width=10.0, opening=2.0, g=9.81)
    
    pump = PumpStation(position=35000.0, width=10.0, rated_flow=50.0,
                      rated_head=5.0, min_suction_head=2.0)
    pump.is_running = True
    
    solver = HydrostaticCanalSolver(
        length=50000.0, nx=251, B=10.0, S0=0.0, n=0.025, eps_dry=0.01,
        internal_structures=[(15000.0, gate), (35000.0, pump)]
    )
    
    # 稳态求解
    result = solver.solve_steady_state(Q_target=20.0, h_downstream=3.0,
                                      max_iterations=2000, verbose=False)
    
    # 验证泵站扬程
    pump_idx = np.argmin(np.abs(solver.x - 35000.0))
    h_up = solver.h[pump_idx - 1]
    h_down = solver.h[pump_idx + 1]
    actual_head = h_down - h_up
    precision = actual_head / 5.0 * 100
    
    # 验证流量守恒
    Q_actual = np.mean(solver.get_Q())
    Q_error = abs(Q_actual - 20.0) / 20.0 * 100
    
    print(f"  泵站扬程: {actual_head:.4f} m (精度 {precision:.1f}%)")
    print(f"  流量守恒: {Q_actual:.4f} m³/s (误差 {Q_error:.3f}%)")
    
    passed = (90 <= precision <= 110) and (Q_error < 1.0)
    print(f"\n结果: {' 通过' if passed else ' 失败'}")
    return passed


def main():
    """主测试程序"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "串联闸泵群全面工况测试" + " " * 22 + "║")
    print("╚" + "=" * 78 + "╝")
    
    test_cases = [
        ("稳态-不同流量", test_case_1_steady_different_flows),
        ("非恒定流-泵站启动", test_case_2_pump_startup),
        ("非恒定流-泵站关闭", test_case_3_pump_shutdown),
        ("非恒定流-流量阶跃", test_case_4_flow_step_change),
        ("稳态-双泵站系统", test_case_5_two_pumps),
        ("稳态-闸泵联合", test_case_6_gate_pump_interaction),
    ]
    
    results = []
    
    for name, test_func in test_cases:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n 测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 80)
    print("全面工况测试总结")
    print("=" * 80)
    
    for name, passed in results:
        status = " 通过" if passed else " 失败"
        print(f"  {name:20s}: {status}")
    
    all_passed = all(r[1] for r in results)
    passed_count = sum(1 for r in results if r[1])
    total_count = len(results)
    
    print("\n" + "=" * 80)
    if all_passed:
        print(f" 全部测试通过！({passed_count}/{total_count})")
        print("   各种工况下精度都满足要求")
    else:
        print(f"️  部分测试失败 ({passed_count}/{total_count})")
        print("   需要进一步优化")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
