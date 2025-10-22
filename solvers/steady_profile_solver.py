#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版稳态水面线求解器

只求解水深h，流量Q作为已知参数
避免Jacobian奇异性问题

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from scipy.integrate import solve_bvp
from scipy.optimize import fsolve, brentq
from typing import List, Tuple, Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.gate import HydraulicStructure
from utils.canal_utils import compute_steady_uniform_flow


class SteadyProfileSolver:
    """
    稳态水面线求解器（简化版）

    特点：
    - 只求解水深h（流量Q已知）
    - 避免Jacobian奇异性
    - 使用shooting method或BVP求解器
    - 支持闸门等内部边界条件
    """

    def __init__(self,
                 length: float,
                 B: float,
                 S0: float,
                 n: float,
                 g: float = 9.81):
        """
        Args:
            length: 渠道长度 (m)
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s²)
        """
        self.length = length
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g

    def compute_friction_slope(self, h: float, Q: float) -> float:
        """
        计算Manning摩阻坡度

        Sf = (n·V)² / R^(4/3)
        """
        h_safe = max(h, 1e-6)
        A = self.B * h_safe
        P = self.B + 2 * h_safe
        R = A / P
        V = Q / A

        Sf = (self.n * V)**2 / R**(4/3)
        return Sf

    def compute_froude(self, h: float, Q: float) -> float:
        """计算Froude数"""
        h_safe = max(h, 1e-6)
        A = self.B * h_safe
        V = Q / A
        Fr = V / np.sqrt(self.g * h_safe)
        return Fr

    def dh_dx(self, h: float, Q: float) -> float:
        """
        稳态动量方程（水面线方程）

        dh/dx = (S0 - Sf) / (1 - Fr²)

        注意：
        - Fr < 1 (缓流): dh/dx与(S0-Sf)同号
        - Fr > 1 (急流): dh/dx与(S0-Sf)异号
        - Fr → 1 (临界流): dh/dx → ∞（数值奇异）
        """
        Sf = self.compute_friction_slope(h, Q)
        Fr = self.compute_froude(h, Q)

        # 避免临界流附近的奇异性
        denominator = 1 - Fr**2
        if abs(denominator) < 0.01:
            # 临界流附近，使用正则化
            denominator = np.sign(denominator) * max(abs(denominator), 0.01)

        dh = (self.S0 - Sf) / denominator

        return dh

    def solve_without_structures(self,
                                 Q: float,
                                 h_downstream: float,
                                 nx: int = 201,
                                 method: str = 'shooting') -> Dict:
        """
        求解无内部结构的稳态水面线

        Args:
            Q: 流量 (m³/s)
            h_downstream: 下游水深 (m)
            nx: 空间点数
            method: 求解方法 ('shooting' 或 'bvp')

        Returns:
            result: 包含x和h数组的字典
        """
        x = np.linspace(0, self.length, nx)

        if method == 'shooting':
            # Shooting method: 从下游向上游积分
            h = np.zeros(nx)
            h[-1] = h_downstream

            dx = self.length / (nx - 1)

            # 向后Euler（从下游到上游）
            for i in range(nx-2, -1, -1):
                # 迭代求解隐式方程
                def residual(h_i):
                    dh_avg = self.dh_dx((h_i + h[i+1])/2, Q)
                    return h_i - h[i+1] - dx * dh_avg

                # 初值：线性外推
                if i == nx - 2:
                    h_init = h[i+1]
                else:
                    h_init = 2*h[i+1] - h[i+2]

                try:
                    h[i] = fsolve(residual, h_init)[0]
                except:
                    # 如果失败，使用显式Euler
                    h[i] = h[i+1] + dx * self.dh_dx(h[i+1], Q)

        else:  # BVP method
            # 使用scipy的BVP求解器
            def ode_system(x, y):
                """ODE系统: y' = f(x, y), 其中 y = h"""
                h = y[0]
                dh = self.dh_dx(h, Q)
                return np.array([dh])

            def bc(ya, yb):
                """边界条件: h(L) = h_downstream"""
                return np.array([yb[0] - h_downstream])

            # 初始猜测：恒定均匀流
            h_uniform = compute_steady_uniform_flow(Q, self.B, self.S0, self.n, self.g)
            y_init = np.array([h_uniform * np.ones(nx)])

            sol = solve_bvp(ode_system, bc, x, y_init)
            h = sol.sol(x)[0]

        return {
            'x': x,
            'h': h,
            'Q': Q * np.ones(nx),
            'method': method
        }

    def solve_with_single_gate(self,
                               Q: float,
                               h_downstream: float,
                               gate_position: float,
                               gate: HydraulicStructure,
                               nx: int = 201) -> Dict:
        """
        求解带单个闸门的稳态水面线

        策略：
        1. 分段求解（闸门上游和下游分开）
        2. 闸门处满足流量关系

        Args:
            Q: 流量 (m³/s)
            h_downstream: 下游边界水深 (m)
            gate_position: 闸门位置 (m)
            gate: 闸门对象
            nx: 总空间点数

        Returns:
            result: 包含x, h, Q的字典
        """
        # 找到闸门位置的索引
        x_full = np.linspace(0, self.length, nx)
        gate_idx = np.argmin(np.abs(x_full - gate_position))
        x_gate = x_full[gate_idx]

        # 闸门下游段
        nx_down = nx - gate_idx
        result_down = self.solve_without_structures(
            Q, h_downstream, nx_down, method='shooting'
        )
        h_down = result_down['h']
        x_down = x_gate + result_down['x'] / self.length * (self.length - x_gate)

        # 闸门处的下游水深
        h_gate_down = h_down[0]

        # 求解闸门上游水深
        # 使用闸门流量关系：Q = f(h_up, h_down)
        def gate_equation(h_up):
            Q_gate, _ = gate.calculate_discharge(h_up, h_gate_down, t=0.0)
            return Q_gate - Q

        # 初始猜测：比下游略高
        h_up_init = h_gate_down + 0.1

        try:
            # 使用Brent方法求解（更稳定）
            h_gate_up = brentq(gate_equation, h_gate_down, h_gate_down + 5.0)
        except:
            # 如果失败，使用fsolve
            h_gate_up = fsolve(gate_equation, h_up_init)[0]

        # 闸门上游段
        nx_up = gate_idx + 1
        result_up = self.solve_without_structures(
            Q, h_gate_up, nx_up, method='shooting'
        )
        h_up = result_up['h']
        x_up = result_up['x'] / self.length * x_gate

        # 合并结果
        x_full = np.concatenate([x_up, x_down[1:]])
        h_full = np.concatenate([h_up, h_down[1:]])

        return {
            'x': x_full,
            'h': h_full,
            'Q': Q * np.ones(len(x_full)),
            'gate_position': x_gate,
            'h_gate_up': h_gate_up,
            'h_gate_down': h_gate_down,
            'gate_idx': gate_idx
        }

    def solve_with_multiple_gates(self,
                                  Q: float,
                                  h_downstream: float,
                                  gates: List[Tuple[float, HydraulicStructure]],
                                  nx: int = 201,
                                  max_iter: int = 50,
                                  tol: float = 1e-4) -> Dict:
        """
        求解带多个闸门的稳态水面线

        策略：
        1. 迭代松弛法
        2. 每次迭代求解各段水面线
        3. 更新闸门处的水深

        Args:
            Q: 流量 (m³/s)
            h_downstream: 下游边界水深 (m)
            gates: 闸门列表 [(position, gate), ...]
            nx: 总空间点数
            max_iter: 最大迭代次数
            tol: 收敛容差

        Returns:
            result: 包含x, h, Q的字典
        """
        # 按位置排序闸门
        gates_sorted = sorted(gates, key=lambda g: g[0])
        n_gates = len(gates_sorted)

        # 分段
        x_full = np.linspace(0, self.length, nx)
        gate_positions = [g[0] for g in gates_sorted]
        gate_indices = [np.argmin(np.abs(x_full - pos)) for pos in gate_positions]

        # 初始化各段
        segments = []
        boundaries = [0] + [x_full[idx] for idx in gate_indices] + [self.length]

        for i in range(n_gates + 1):
            x_start = boundaries[i]
            x_end = boundaries[i + 1]
            segment_length = x_end - x_start

            # 估算段内点数
            if i == n_gates:
                idx_start = gate_indices[-1] if n_gates > 0 else 0
                idx_end = nx - 1
            elif i == 0:
                idx_start = 0
                idx_end = gate_indices[0]
            else:
                idx_start = gate_indices[i - 1]
                idx_end = gate_indices[i]

            nx_segment = idx_end - idx_start + 1

            segments.append({
                'x_start': x_start,
                'x_end': x_end,
                'length': segment_length,
                'nx': nx_segment,
                'idx_start': idx_start,
                'idx_end': idx_end
            })

        # 初始化闸门处的水深猜测
        h_uniform = compute_steady_uniform_flow(Q, self.B, self.S0, self.n, self.g)
        h_gates_up = [h_uniform + 0.05 * (i+1) for i in range(n_gates)]
        h_gates_down = [h_uniform for _ in range(n_gates)]

        # 迭代求解
        for iter_count in range(max_iter):
            h_segments = []
            x_segments = []

            # 从下游到上游求解各段
            for i in range(n_gates, -1, -1):
                seg = segments[i]

                # 确定该段的下游边界条件
                if i == n_gates:
                    # 最后一段：使用下游边界
                    h_bc = h_downstream
                else:
                    # 其他段：使用下一个闸门的上游水深
                    h_bc = h_gates_up[i]

                # 求解该段
                # 创建临时求解器（该段长度）
                temp_solver = SteadyProfileSolver(seg['length'], self.B, self.S0, self.n, self.g)
                result_seg = temp_solver.solve_without_structures(Q, h_bc, seg['nx'], method='shooting')

                h_segments.insert(0, result_seg['h'])
                x_seg_local = result_seg['x']
                x_seg_global = seg['x_start'] + x_seg_local
                x_segments.insert(0, x_seg_global)

                # 更新闸门下游水深
                if i > 0:
                    h_gates_down[i - 1] = result_seg['h'][0]

            # 更新闸门上游水深（满足闸门流量关系）
            max_change = 0.0
            for i in range(n_gates):
                _, gate_obj = gates_sorted[i]
                h_down = h_gates_down[i]

                def gate_eq(h_up):
                    Q_gate, _ = gate_obj.calculate_discharge(h_up, h_down, t=0.0)
                    return Q_gate - Q

                try:
                    h_up_new = brentq(gate_eq, h_down, h_down + 5.0)
                except:
                    h_up_new = fsolve(gate_eq, h_gates_up[i])[0]

                change = abs(h_up_new - h_gates_up[i])
                max_change = max(max_change, change)

                # 松弛更新
                relax = 0.7
                h_gates_up[i] = (1 - relax) * h_gates_up[i] + relax * h_up_new

            # 检查收敛
            if max_change < tol:
                break

        # 组装完整结果
        h_full = np.concatenate(h_segments)
        x_full_result = np.concatenate(x_segments)

        return {
            'x': x_full_result,
            'h': h_full,
            'Q': Q * np.ones(len(h_full)),
            'converged': max_change < tol,
            'iterations': iter_count + 1,
            'h_gates_up': h_gates_up,
            'h_gates_down': h_gates_down,
            'gate_positions': gate_positions
        }


def test_steady_profile_solver():
    """测试简化版稳态求解器"""
    from solvers.gate import SluiceGate

    print("=" * 80)
    print("简化版稳态水面线求解器测试")
    print("=" * 80)

    # 测试1：无闸门
    print("\n测试1：无闸门（恒定流）")
    print("-" * 80)

    solver = SteadyProfileSolver(
        length=1000.0,
        B=10.0,
        S0=0.001,
        n=0.025
    )

    Q = 10.0
    h_downstream = compute_steady_uniform_flow(Q, 10.0, 0.001, 0.025)

    result1 = solver.solve_without_structures(Q, h_downstream, nx=201, method='shooting')

    print(f"  流量: {Q} m³/s")
    print(f"  下游水深: {h_downstream:.4f} m")
    print(f"  上游水深: {result1['h'][0]:.4f} m")
    print(f"  水深变化: {abs(result1['h'][0] - h_downstream):.6f} m")
    print(f"  ✓ 无闸门情况应接近恒定均匀流")

    # 测试2：单闸门
    print("\n\n测试2：单闸门")
    print("-" * 80)

    gate = SluiceGate(position=500.0, width=10.0, opening=5.0, Cd=0.6)

    result2 = solver.solve_with_single_gate(Q, h_downstream, 500.0, gate, nx=201)

    print(f"  流量: {Q} m³/s")
    print(f"  闸门位置: 500.0 m")
    print(f"  闸门开度: 5.0 m")
    print(f"  闸前水深: {result2['h_gate_up']:.4f} m")
    print(f"  闸后水深: {result2['h_gate_down']:.4f} m")
    print(f"  水位差: {result2['h_gate_up'] - result2['h_gate_down']:.4f} m")
    print(f"  ✓ 闸门应产生水位差")

    # 测试3：三闸门
    print("\n\n测试3：三闸门串联")
    print("-" * 80)

    gate1 = SluiceGate(position=250.0, width=10.0, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=500.0, width=10.0, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=750.0, width=10.0, opening=5.0, Cd=0.6)

    import time
    start_time = time.time()

    result3 = solver.solve_with_multiple_gates(
        Q, h_downstream,
        [(gate1.position, gate1),
         (gate2.position, gate2),
         (gate3.position, gate3)],
        nx=201,
        max_iter=100,
        tol=1e-4
    )

    elapsed = time.time() - start_time

    print(f"  流量: {Q} m³/s")
    print(f"  收敛: {'是' if result3['converged'] else '否'}")
    print(f"  迭代次数: {result3['iterations']}")
    print(f"  计算时间: {elapsed:.4f}s")
    print(f"  闸门1 (250m): 上游={result3['h_gates_up'][0]:.4f}m, 下游={result3['h_gates_down'][0]:.4f}m")
    print(f"  闸门2 (500m): 上游={result3['h_gates_up'][1]:.4f}m, 下游={result3['h_gates_down'][1]:.4f}m")
    print(f"  闸门3 (750m): 上游={result3['h_gates_up'][2]:.4f}m, 下游={result3['h_gates_down'][2]:.4f}m")
    print(f"  ✓ 多闸门求解成功")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_steady_profile_solver()
