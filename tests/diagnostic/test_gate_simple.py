#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单闸门测试 - 验证闸门边界条件是否正确工作

测试策略：
1. 使用合理的下游边界条件（均匀流水深）
2. 验证闸门流量公式是否满足
3. 验证流量守恒
"""

import numpy as np
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


def test_simple_gate():
    """简单闸门测试"""
    print("=" * 70)
    print("简单闸门测试")
    print("=" * 70)

    # 参数
    L = 1000.0
    B = 10.0
    S0 = 0.001
    n = 0.025
    g = 9.81

    Q_target = 5.0
    gate_position = 500.0
    gate_opening = 0.5
    gate_Cd = 0.6

    # 计算下游边界条件（均匀流水深）
    h_downstream = compute_uniform_flow(Q_target, B, S0, n)

    print(f"\n参数设置：")
    print(f"  渠道：L={L}m, B={B}m, S0={S0}, n={n}")
    print(f"  流量：Q={Q_target} m^3/s")
    print(f"  闸门：位置={gate_position}m, 开度={gate_opening}m, Cd={gate_Cd}")
    print(f"  下游边界：h={h_downstream:.4f}m（均匀流水深）")

    # 创建闸门
    gate = SluiceGate(
        position=gate_position,
        width=B,
        opening=gate_opening,
        Cd=gate_Cd,
        g=g
    )

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=L,
        nx=101,
        B=B,
        S0=S0,
        n=n,
        g=g,
        internal_structures=[(gate_position, gate)]
    )

    print(f"\n开始求解...")

    # 求解稳态
    result = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=h_downstream,
        max_iterations=3000,
        convergence_tol=0.001,
        dt=0.5,
        verbose=True
    )

    # 分析结果
    print(f"\n结果分析：")
    print(f"  收敛：{result['converged']}")
    print(f"  迭代次数：{result['iterations']}")

    # 流量守恒
    print(f"\n流量守恒：")
    print(f"  目标：{Q_target:.4f} m^3/s")
    print(f"  实际：{result['Q_mean']:.4f} m^3/s")
    print(f"  误差：{result['Q_error_percent']:.2f}%")

    # 闸门验证
    gate_idx = solver.structure_indices[0]
    h_up = result['h'][gate_idx - 1]
    h_down = result['h'][gate_idx + 1]
    Q_gate, flow_type = gate.calculate_discharge(h_up, h_down)

    print(f"\n闸门验证：")
    print(f"  上游水深：{h_up:.4f} m")
    print(f"  下游水深：{h_down:.4f} m")
    print(f"  水位差：{h_up - h_down:.4f} m")
    print(f"  闸门流量：{Q_gate:.4f} m^3/s")
    print(f"  流态：{flow_type}")
    print(f"  闸门流量误差：{abs(Q_gate - Q_target) / Q_target * 100:.2f}%")

    # 判断测试结果
    mass_ok = result['Q_error_percent'] < 5.0
    gate_ok = abs(Q_gate - Q_target) / Q_target * 100 < 5.0
    converged_ok = result['converged']
    water_level_ok = h_up > h_down

    print(f"\n测试结果：")
    print(f"  流量守恒：{' PASS' if mass_ok else ' FAIL'} ({result['Q_error_percent']:.2f}% < 5%)")
    print(f"  闸门流量：{' PASS' if gate_ok else ' FAIL'} ({abs(Q_gate - Q_target) / Q_target * 100:.2f}% < 5%)")
    print(f"  收敛性：{' PASS' if converged_ok else ' FAIL'}")
    print(f"  水位关系：{' PASS' if water_level_ok else ' FAIL'}")

    overall = mass_ok and gate_ok and converged_ok and water_level_ok
    print(f"\n总体：{' 全部通过' if overall else ' 存在问题'}")
    print("=" * 70)

    return overall


if __name__ == "__main__":
    success = test_simple_gate()
    sys.exit(0 if success else 1)
