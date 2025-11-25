#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三闸门系统测试 - 使用静水重构求解器

验证HydrostaticCanalSolver能否处理三闸门复杂系统
目标：流量误差 < 0.5%

配置：
- 渠道长度：10000m
- 三个闸门：x=2500m, 5000m, 7500m
- 流量：10 m^3/s
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
import sys
sys.path.append('.')

try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import SluiceGate


def compute_uniform_flow(Q, B, S0, n):
    """计算均匀流水深"""
    h = 1.0
    for i in range(100):
        A = B * h
        R = A / (B + 2*h)
        Q_calc = (1/n) * A * R**(2/3) * np.sqrt(S0)
        if abs(Q - Q_calc) < 1e-6:
            break
        dQ_dh = (1/n) * np.sqrt(S0) * (B * R**(2/3) + A * (2/3) * R**(-1/3) * (B - 2*h) / (B + 2*h)**2)
        h = h + (Q - Q_calc) / dQ_dh
        h = max(0.1, h)
    return h


def test_three_gates():
    """测试三闸门系统"""
    print("=" * 80)
    print("三闸门系统测试 - HydrostaticCanalSolver")
    print("=" * 80)

    # 渠道参数
    length = 10000.0
    nx = 301
    B = 10.0
    S0 = 0.0005
    n = 0.025
    Q_target = 10.0
    g = 9.81

    # 三个闸门配置
    gate1_pos = 2500.0
    gate1_opening = 4.5
    gate2_pos = 5000.0
    gate2_opening = 4.0
    gate3_pos = 7500.0
    gate3_opening = 5.0
    Cd = 0.6

    # 计算均匀流水深
    h_uniform = compute_uniform_flow(Q_target, B, S0, n)

    print(f"\n渠道参数：")
    print(f"  长度：{length} m")
    print(f"  网格点数：{nx}")
    print(f"  宽度：{B} m")
    print(f"  底坡：{S0}")
    print(f"  Manning糙率：{n}")
    print(f"  目标流量：{Q_target} m^3/s")
    print(f"  均匀流水深：{h_uniform:.4f} m")

    print(f"\n闸门配置：")
    print(f"  闸门1：x={gate1_pos}m, 开度={gate1_opening}m")
    print(f"  闸门2：x={gate2_pos}m, 开度={gate2_opening}m")
    print(f"  闸门3：x={gate3_pos}m, 开度={gate3_opening}m")
    print(f"  流量系数：Cd={Cd}")

    # 创建闸门对象
    gate1 = SluiceGate(gate1_pos, B, gate1_opening, Cd, g)
    gate2 = SluiceGate(gate2_pos, B, gate2_opening, Cd, g)
    gate3 = SluiceGate(gate3_pos, B, gate3_opening, Cd, g)

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=length,
        nx=nx,
        B=B,
        S0=S0,
        n=n,
        g=g,
        internal_structures=[
            (gate1_pos, gate1),
            (gate2_pos, gate2),
            (gate3_pos, gate3)
        ]
    )

    print(f"\n求解器设置：")
    print(f"  网格间距：{solver.dx:.2f} m")
    print(f"  闸门节点索引：{solver.structure_indices}")
    print(f"  Preissmann参数：θ={solver.theta}, ω={solver.omega}")

    # 求解稳态
    print(f"\n开始稳态求解...")
    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_uniform,
        max_iterations=5000,
        convergence_tol=0.001,
        dt=0.5,
        verbose=True
    )

    # 分析结果
    print(f"\n=" * 80)
    print(f"结果分析")
    print(f"=" * 80)
    print(f"  收敛状态：{' 收敛' if result['converged'] else ' 未收敛'}")
    print(f"  迭代次数：{result['iterations']}")

    # 流量守恒
    print(f"\n流量守恒：")
    print(f"  目标流量：{Q_target:.4f} m^3/s")
    print(f"  实际流量：{result['Q_mean']:.4f} m^3/s")
    print(f"  误差：{result['Q_error_percent']:.4f}%")

    # 验证每个闸门
    print(f"\n闸门流量验证：")
    for i, (idx, gate, name) in enumerate(zip(
        solver.structure_indices,
        solver.structure_objects,
        ['闸门1', '闸门2', '闸门3']
    )):
        h_up = result['h'][idx - 1]
        h_down = result['h'][idx + 1]
        Q_gate, flow_type = gate.calculate_discharge(h_up, h_down)
        gate_error = abs(Q_gate - Q_target) / Q_target * 100

        print(f"  {name}:")
        print(f"    上游水深：{h_up:.4f} m")
        print(f"    下游水深：{h_down:.4f} m")
        print(f"    水位差：{h_up - h_down:.4f} m")
        print(f"    流量：{Q_gate:.4f} m^3/s（误差{gate_error:.2f}%）")
        print(f"    流态：{flow_type}")

    # 水深分布统计
    print(f"\n水深分布：")
    print(f"  范围：[{result['h'].min():.4f}, {result['h'].max():.4f}] m")
    print(f"  均值：{result['h'].mean():.4f} m")

    # 判断测试结果
    mass_ok = result['Q_error_percent'] < 0.5  # 目标：0.5%
    converged_ok = result['converged']

    print(f"\n测试结果：")
    print(f"  流量守恒：{' PASS' if mass_ok else ' FAIL'} ({result['Q_error_percent']:.4f}% < 0.5%)")
    print(f"  收敛性：{' PASS' if converged_ok else ' FAIL'}")

    overall = mass_ok and converged_ok
    print(f"\n总体结论：{' 达到目标精度！' if overall else ' 未达目标'}")
    print("=" * 80)

    # 绘图
    print(f"\n生成图表...")
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    x = solver.x

    # 图1：水深分布
    ax = axes[0]
    ax.plot(x, result['h'], 'b-', linewidth=2, label='Water depth')
    ax.axhline(h_uniform, color='r', linestyle='--', linewidth=1.5,
               label=f'Uniform flow ({h_uniform:.3f}m)', alpha=0.7)
    for gate_pos, name in [(gate1_pos, 'Gate 1'), (gate2_pos, 'Gate 2'), (gate3_pos, 'Gate 3')]:
        ax.axvline(gate_pos, color='gray', linestyle=':', alpha=0.5)
        ax.text(gate_pos, ax.get_ylim()[1]*0.95, name, ha='center', fontsize=9)
    ax.set_ylabel('Water depth (m)')
    ax.set_title(f'Three Gates System: Steady State (Q={Q_target} m^3/s)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 图2：流量分布
    ax = axes[1]
    ax.plot(x, result['Q'], 'g-', linewidth=2, label='Discharge')
    ax.axhline(Q_target, color='k', linestyle='--', linewidth=1.5,
               label=f'Target ({Q_target} m^3/s)')
    for gate_pos in [gate1_pos, gate2_pos, gate3_pos]:
        ax.axvline(gate_pos, color='gray', linestyle=':', alpha=0.5)
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title(f'Discharge Distribution (error={result["Q_error_percent"]:.4f}%)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 图3：水位剖面
    ax = axes[2]
    eta = result['h'] + solver.z
    ax.plot(x, eta, 'r-', linewidth=2, label='Water surface')
    ax.fill_between(x, solver.z, alpha=0.3, color='brown', label='Bed')
    for gate_pos, name in [(gate1_pos, 'Gate 1'), (gate2_pos, 'Gate 2'), (gate3_pos, 'Gate 3')]:
        ax.axvline(gate_pos, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Elevation (m)')
    ax.set_title('Water Surface Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('three_gates_hydrostatic_test.png', dpi=150)
    print(f"  图表保存至：three_gates_hydrostatic_test.png")

    return overall, result


if __name__ == "__main__":
    success, result = test_three_gates()
    sys.exit(0 if success else 1)
