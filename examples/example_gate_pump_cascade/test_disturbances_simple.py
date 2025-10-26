#!/usr/bin/env python3
"""
串联闸泵群系统综合扰动测试（简化版）
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys

sys.path.insert(0, '/workspace')

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PumpStation


def setup_system():
    """建立系统"""
    print("\n" + "=" * 80)
    print("串联闸泵群系统 - 综合扰动测试")
    print("=" * 80)
    
    L = 100000
    nx = 501
    B = 10.0
    
    gate1 = SluiceGate(position=20000, width=B, opening=1.5)
    pump1 = PumpStation(position=35000, width=B, rated_flow=10.0, rated_head=3.0)
    gate2 = SluiceGate(position=50000, width=B, opening=2.0)
    pump2 = PumpStation(position=65000, width=B, rated_flow=10.0, rated_head=4.0)
    gate3 = SluiceGate(position=80000, width=B, opening=1.8)
    
    structures = [
        (20000, gate1),
        (35000, pump1),
        (50000, gate2),
        (65000, pump2),
        (80000, gate3)
    ]
    
    solver = HydrostaticCanalSolver(
        length=L,
        nx=nx,
        B=B,
        S0=0.0001,
        n=0.025,
        internal_structures=structures
    )
    
    print(f"\n系统配置:")
    print(f"  渠道长度: {L/1000:.1f} km")
    print(f"  结构物: 3个闸门 + 2个泵站")
    
    return solver, structures


def run_scenario(solver, scenario_name, nt=150, dt=10.0, disturbance_func=None):
    """运行场景"""
    print(f"\n{'='*80}")
    print(f"场景: {scenario_name}")
    print(f"{'='*80}")
    
    # 稳态初始化
    print(f"\n稳态初始化...")
    result = solver.solve_steady_state(
        Q_target=10.0,
        h_downstream=2.0,
        max_iterations=500,
        convergence_tol=0.001,
        dt=0.5,
        verbose=False
    )
    print(f"  收敛: {result['converged']}, 迭代: {result['iterations']}")
    
    # 记录数据
    times = np.arange(nt) * dt
    h_history = np.zeros((nt, solver.nx))
    Q_history = np.zeros((nt, solver.nx))
    
    # 初始边界条件
    Q_in = 10.0
    h_down = 2.0
    
    print(f"\n非恒定流模拟 (t=0-{nt*dt:.0f}s):")
    
    for i in range(nt):
        # 应用扰动
        if disturbance_func:
            Q_in, h_down = disturbance_func(i, dt, solver)
        
        # Preissmann步
        h_new, hu_new = solver.step_preissmann(dt)
        
        # 边界条件
        hu_new[0] = Q_in / solver.B
        h_new[-1] = h_down
        
        # 更新
        solver.h = h_new
        solver.hu = hu_new
        
        # 内部边界条件
        solver._apply_pump_head_jump()
        if solver.structure_indices:
            solver._apply_internal_bc(t=i*dt, Q_target=Q_in)
        
        # 记录
        h_history[i, :] = solver.h
        Q_history[i, :] = solver.get_Q()
        
        if i % 30 == 0:
            Q_avg = np.mean(Q_history[i, :])
            Q_std = np.std(Q_history[i, :])
            print(f"  t={i*dt:5.0f}s: Q_in={Q_in:.1f}, Q_avg={Q_avg:.2f}±{Q_std:.2f} m³/s")
    
    return times, h_history, Q_history


def analyze_results(times, h_history, Q_history, solver, scenario_name):
    """分析结果"""
    print(f"\n结果分析:")
    
    # 流量守恒
    Q_in = Q_history[:, 0]
    Q_out = Q_history[:, -1]
    Q_avg = np.mean(Q_history, axis=1)
    
    print(f"  流量统计:")
    print(f"    入流: {np.mean(Q_in):.2f}±{np.std(Q_in):.2f} m³/s")
    print(f"    出流: {np.mean(Q_out):.2f}±{np.std(Q_out):.2f} m³/s")
    print(f"    平均: {np.mean(Q_avg):.2f}±{np.std(Q_avg):.2f} m³/s")
    
    # 水位统计
    h_max = np.max(h_history)
    h_min = np.min(h_history)
    h_mean = np.mean(h_history)
    
    print(f"  水深统计:")
    print(f"    最大: {h_max:.2f} m")
    print(f"    最小: {h_min:.2f} m")
    print(f"    平均: {h_mean:.2f} m")
    
    # 检查数值稳定性
    has_nan = np.isnan(h_history).any() or np.isnan(Q_history).any()
    has_inf = np.isinf(h_history).any() or np.isinf(Q_history).any()
    
    if has_nan:
        print(f"  ⚠️ 警告: 发现NaN值")
    if has_inf:
        print(f"  ⚠️ 警告: 发现Inf值")
    
    if not has_nan and not has_inf:
        print(f"  ✓ 数值稳定")
    
    return {
        'Q_conservation': (np.mean(Q_in), np.mean(Q_out), np.mean(Q_avg)),
        'h_range': (h_min, h_max, h_mean),
        'stable': not (has_nan or has_inf)
    }


def plot_results(times, h_history, Q_history, solver, scenario_name):
    """绘制结果"""
    x = solver.x / 1000
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    
    # 子图1: 水位时空图
    ax1 = axes[0]
    im1 = ax1.contourf(x, times/60, h_history, levels=20, cmap='viridis')
    plt.colorbar(im1, ax=ax1, label='水深 (m)')
    ax1.set_ylabel('时间 (min)')
    ax1.set_title(f'{scenario_name} - 水深时空演化', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 标记结构物
    for pos in [20, 35, 50, 65, 80]:
        ax1.axvline(pos, color='white', linestyle='--', alpha=0.5, linewidth=0.8)
    
    # 子图2: 流量时空图
    ax2 = axes[1]
    im2 = ax2.contourf(x, times/60, Q_history, levels=20, cmap='RdYlGn')
    plt.colorbar(im2, ax=ax2, label='流量 (m³/s)')
    ax2.set_ylabel('时间 (min)')
    ax2.set_title('流量时空演化', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    for pos in [20, 35, 50, 65, 80]:
        ax2.axvline(pos, color='white', linestyle='--', alpha=0.5, linewidth=0.8)
    
    # 子图3: 关键点时间序列
    ax3 = axes[2]
    
    # 选择关键位置
    idx_20 = np.argmin(np.abs(x - 20))
    idx_50 = np.argmin(np.abs(x - 50))
    idx_80 = np.argmin(np.abs(x - 80))
    
    ax3.plot(times/60, Q_history[:, 0], 'b-', label='上游入流', linewidth=2)
    ax3.plot(times/60, Q_history[:, idx_20], 'g--', label='闸门1 (20km)', alpha=0.7)
    ax3.plot(times/60, Q_history[:, idx_50], 'r--', label='闸门2 (50km)', alpha=0.7)
    ax3.plot(times/60, Q_history[:, idx_80], 'm--', label='闸门3 (80km)', alpha=0.7)
    ax3.plot(times/60, Q_history[:, -1], 'k-', label='下游出流', linewidth=2)
    
    ax3.set_xlabel('时间 (min)')
    ax3.set_ylabel('流量 (m³/s)')
    ax3.set_title('关键位置流量时间序列', fontsize=12, fontweight='bold')
    ax3.legend(loc='best', ncol=2)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    filename = f"result_{scenario_name}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ 结果图已保存: {filename}")


def main():
    """主函数"""
    
    scenarios = []
    
    # 场景1: 上游流量阶跃
    print("\n" + "=" * 80)
    print("场景1: 上游流量阶跃 (10 → 15 m³/s)")
    print("=" * 80)
    
    solver1, _ = setup_system()
    
    def disturbance1(i, dt, solver):
        Q_in = 10.0 if i < 60 else 15.0
        if i == 60:
            print(f"  t={i*dt:.0f}s: [扰动] 上游流量 10.0 → 15.0 m³/s")
        return Q_in, 2.0
    
    times1, h1, Q1 = run_scenario(solver1, "场景1_上游流量阶跃", nt=150, dt=10.0, disturbance_func=disturbance1)
    stats1 = analyze_results(times1, h1, Q1, solver1, "场景1")
    plot_results(times1, h1, Q1, solver1, "场景1_上游流量阶跃")
    scenarios.append(("场景1", stats1))
    
    # 场景2: 闸门调节
    print("\n" + "=" * 80)
    print("场景2: 闸门动态调节")
    print("=" * 80)
    
    solver2, structures2 = setup_system()
    gate2 = structures2[2][1]  # 中间闸门
    
    def disturbance2(i, dt, solver):
        if i == 40:
            gate2.opening = 1.0
            print(f"  t={i*dt:.0f}s: [扰动] 闸门2开度 2.0 → 1.0 m")
        elif i == 100:
            gate2.opening = 2.5
            print(f"  t={i*dt:.0f}s: [扰动] 闸门2开度 1.0 → 2.5 m")
        return 10.0, 2.0
    
    times2, h2, Q2 = run_scenario(solver2, "场景2_闸门调节", nt=150, dt=10.0, disturbance_func=disturbance2)
    stats2 = analyze_results(times2, h2, Q2, solver2, "场景2")
    plot_results(times2, h2, Q2, solver2, "场景2_闸门调节")
    scenarios.append(("场景2", stats2))
    
    # 场景3: 泵站控制
    print("\n" + "=" * 80)
    print("场景3: 泵站启停控制")
    print("=" * 80)
    
    solver3, structures3 = setup_system()
    pump1 = structures3[1][1]
    
    def disturbance3(i, dt, solver):
        if i == 50:
            pump1.is_running = False
            print(f"  t={i*dt:.0f}s: [扰动] 泵站1 关闭")
        elif i == 110:
            pump1.is_running = True
            print(f"  t={i*dt:.0f}s: [扰动] 泵站1 启动")
        return 10.0, 2.0
    
    times3, h3, Q3 = run_scenario(solver3, "场景3_泵站控制", nt=150, dt=10.0, disturbance_func=disturbance3)
    stats3 = analyze_results(times3, h3, Q3, solver3, "场景3")
    plot_results(times3, h3, Q3, solver3, "场景3_泵站控制")
    scenarios.append(("场景3", stats3))
    
    # 场景4: 下游水位变化
    print("\n" + "=" * 80)
    print("场景4: 下游水位扰动")
    print("=" * 80)
    
    solver4, _ = setup_system()
    
    def disturbance4(i, dt, solver):
        if i < 60:
            h_down = 2.0
        elif i < 110:
            h_down = 2.5
            if i == 60:
                print(f"  t={i*dt:.0f}s: [扰动] 下游水位 2.0 → 2.5 m")
        else:
            h_down = 1.8
            if i == 110:
                print(f"  t={i*dt:.0f}s: [扰动] 下游水位 2.5 → 1.8 m")
        return 10.0, h_down
    
    times4, h4, Q4 = run_scenario(solver4, "场景4_下游水位", nt=150, dt=10.0, disturbance_func=disturbance4)
    stats4 = analyze_results(times4, h4, Q4, solver4, "场景4")
    plot_results(times4, h4, Q4, solver4, "场景4_下游水位")
    scenarios.append(("场景4", stats4))
    
    # 综合报告
    print("\n" + "=" * 80)
    print("综合测试总结")
    print("=" * 80)
    
    for name, stats in scenarios:
        print(f"\n{name}:")
        Q_in, Q_out, Q_avg = stats['Q_conservation']
        print(f"  流量: 入流={Q_in:.2f}, 出流={Q_out:.2f}, 平均={Q_avg:.2f} m³/s")
        h_min, h_max, h_mean = stats['h_range']
        print(f"  水深: 最小={h_min:.2f}, 最大={h_max:.2f}, 平均={h_mean:.2f} m")
        print(f"  稳定性: {'✓ 通过' if stats['stable'] else '✗ 失败'}")
    
    print(f"\n{'='*80}")
    print("✓ 全部测试完成！")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
