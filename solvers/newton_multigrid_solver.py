#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
牛顿-多网格组合求解器

组合牛顿法和多网格方法，用于高效求解稳态Saint-Venant方程

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.newton_solver import NewtonSolver
from solvers.multigrid_solver import MultiGridSolver
from physics.steady_saint_venant import SteadySaintVenantSystem
from solvers.gate import HydraulicStructure
from utils.canal_utils import compute_steady_uniform_flow


class NewtonMultiGridSolver:
    """
    牛顿-多网格组合求解器

    特点：
    - 外层：牛顿法迭代（二次收敛）
    - 内层：多网格求解线性系统（O(N)复杂度）
    - 支持闸门等内部边界条件
    - 自动初始化和边界条件设置
    """

    def __init__(self,
                 length: float,
                 nx: int,
                 B: float,
                 S0: float,
                 n: float,
                 g: float = 9.81,
                 structures: Optional[List[Tuple[float, HydraulicStructure]]] = None,
                 verbose: bool = False):
        """
        Args:
            length: 渠道长度 (m)
            nx: 空间节点数
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s²)
            structures: 水工建筑物列表 [(position, structure), ...]
            verbose: 是否输出详细信息
        """
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.structures = structures if structures is not None else []
        self.verbose = verbose

        # 创建稳态Saint-Venant系统（带伪瞬态延拓）
        self.sv_system = SteadySaintVenantSystem(
            length, nx, B, S0, n, g, structures,
            pseudo_dt=1.0  # 伪时间步长，避免Jacobian奇异
        )

        # 创建牛顿求解器（先用直接求解器测试）
        self.newton_solver = NewtonSolver(
            linear_solver='direct',  # 先用直接求解器
            max_iter=50,
            tol_residual=1e-6,
            tol_update=1e-8,
            line_search=True,
            verbose=verbose
        )

        # 创建多网格求解器（可选）
        self.mg_solver = MultiGridSolver(
            n_levels=None,  # 自动确定
            nu1=2,
            nu2=2,
            verbose=False  # 多网格不单独输出（由牛顿控制）
        )

        # 可以在solve时切换求解器
        self.use_multigrid = False  # 默认不使用多网格

        # 求解历史
        self.solve_history = []

    def solve_steady_state(self,
                          Q_target: float,
                          h_downstream: Optional[float] = None,
                          U_init: Optional[np.ndarray] = None,
                          max_newton_iter: int = 20,
                          tol: float = 1e-6,
                          t: float = 0.0,
                          use_multigrid: bool = False) -> Dict:
        """
        求解稳态Saint-Venant方程

        Args:
            Q_target: 目标流量 (m³/s)
            h_downstream: 下游水深 (m)，None则自动计算
            U_init: 初始状态向量，None则使用恒定均匀流
            max_newton_iter: 最大牛顿迭代次数
            tol: 收敛容差
            t: 当前时间（用于时变结构）

        Returns:
            result: 求解结果字典
                - converged: 是否收敛
                - iterations: 牛顿迭代次数
                - h: 水深数组
                - Q: 流量数组
                - x: 空间坐标
                - residual_norm: 最终残差
                - elapsed_time: 计算时间
                - gate_flows: 闸门流量列表
        """
        if self.verbose:
            print("=" * 80)
            solver_name = "牛顿-多网格求解器" if use_multigrid else "牛顿求解器（直接法）"
            print(f"{solver_name}：稳态求解")
            print("=" * 80)
            print(f"  目标流量: {Q_target} m³/s")
            print(f"  网格点数: {self.nx}")
            print(f"  闸门数量: {len(self.structures)}")

        # 设置求解器类型
        if use_multigrid:
            self.newton_solver.set_multigrid_solver(self.mg_solver)
        else:
            self.newton_solver.linear_solver_type = 'direct'

        start_time = time.time()

        # 设置边界条件
        if h_downstream is None:
            h_downstream = compute_steady_uniform_flow(Q_target, self.B, self.S0, self.n, self.g)

        self.sv_system.set_boundary_conditions(
            Q_upstream=Q_target,
            h_downstream=h_downstream
        )

        if self.verbose:
            print(f"  下游水深: {h_downstream:.4f} m")

        # 初始化状态向量
        if U_init is None:
            h_uniform = compute_steady_uniform_flow(Q_target, self.B, self.S0, self.n, self.g)
            h_init = np.ones(self.nx) * h_uniform
            Q_init = np.ones(self.nx) * Q_target
            U_init = self.sv_system.pack_state(h_init, Q_init)

            if self.verbose:
                print(f"  初始水深: {h_uniform:.4f} m (恒定均匀流)")

        # 定义残差和Jacobian函数
        def residual_func(U):
            return self.sv_system.compute_residual(U, t)

        def jacobian_func(U):
            return self.sv_system.compute_jacobian(U, t)

        # 回调函数：更新伪瞬态的前一步
        def callback(iter_num, U_current, F, dU, alpha):
            # 更新上一步的解
            self.sv_system.U_prev = U_current.copy()

        # 求解
        if self.verbose:
            print(f"\n开始牛顿-多网格迭代...")
            print("-" * 80)

        # 初始化伪瞬态的前一步
        self.sv_system.U_prev = U_init.copy()

        # 更新牛顿求解器参数
        self.newton_solver.max_iter = max_newton_iter
        self.newton_solver.tol_residual = tol

        U_sol, info = self.newton_solver.solve(
            U_init, residual_func, jacobian_func, callback=callback
        )

        elapsed_time = time.time() - start_time

        # 解包结果
        h_sol, Q_sol = self.sv_system.unpack_state(U_sol)

        # 计算闸门流量
        gate_flows = []
        for structure in self.sv_system.structure_objects:
            idx = self.sv_system.structure_indices[self.sv_system.structure_objects.index(structure)]
            if idx > 0 and idx < self.nx - 1:
                h_up = h_sol[idx - 1]
                h_down = h_sol[idx + 1]
                Q_gate, _ = structure.calculate_discharge(h_up, h_down, t)
                gate_flows.append(Q_gate)

        # 汇总结果
        result = {
            'converged': info['converged'],
            'iterations': info['iterations'],
            'h': h_sol,
            'Q': Q_sol,
            'x': self.sv_system.x,
            'residual_norm': info['residual_norm'],
            'residual_history': info['residual_history'],
            'elapsed_time': elapsed_time,
            'gate_flows': gate_flows,
            'convergence_reason': info.get('convergence_reason', 'unknown'),
            'final_error': self._compute_flow_conservation_error(Q_sol, gate_flows)
        }

        # 保存历史
        self.solve_history.append(result)

        if self.verbose:
            print("-" * 80)
            print(f"求解完成：")
            print(f"  收敛: {'是' if result['converged'] else '否'}")
            print(f"  迭代次数: {result['iterations']}")
            print(f"  最终残差: {result['residual_norm']:.3e}")
            print(f"  流量守恒误差: {result['final_error']*100:.4f}%")
            if gate_flows:
                print(f"  闸门流量: {', '.join([f'{q:.3f}' for q in gate_flows])} m³/s")
            print(f"  计算时间: {elapsed_time:.4f}s")
            print("=" * 80)

        return result

    def _compute_flow_conservation_error(self, Q: np.ndarray, gate_flows: List[float]) -> float:
        """
        计算流量守恒误差

        Args:
            Q: 流量数组
            gate_flows: 闸门流量列表

        Returns:
            相对误差
        """
        Q_mean = np.mean(np.abs(Q))
        if Q_mean < 1e-6:
            return 0.0

        # 检查流量变化
        Q_std = np.std(Q)
        error = Q_std / Q_mean

        return error


def test_newton_multigrid():
    """测试牛顿-多网格求解器"""
    from solvers.gate import SluiceGate

    print("=" * 80)
    print("牛顿-多网格求解器测试")
    print("=" * 80)

    # 测试场景1：无闸门
    print("\n场景1：无闸门（恒定流）")
    print("-" * 80)

    solver1 = NewtonMultiGridSolver(
        length=1000.0,
        nx=201,
        B=10.0,
        S0=0.001,
        n=0.025,
        structures=[],
        verbose=True
    )

    result1 = solver1.solve_steady_state(Q_target=10.0)

    # 测试场景2：单闸门
    print("\n\n场景2：单闸门")
    print("-" * 80)

    gate = SluiceGate(position=500.0, width=10.0, opening=5.0, Cd=0.6)

    solver2 = NewtonMultiGridSolver(
        length=1000.0,
        nx=201,
        B=10.0,
        S0=0.001,
        n=0.025,
        structures=[(gate.position, gate)],
        verbose=True
    )

    result2 = solver2.solve_steady_state(Q_target=10.0)

    # 测试场景3：三闸门串联
    print("\n\n场景3：三闸门串联")
    print("-" * 80)

    gate1 = SluiceGate(position=250.0, width=10.0, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=500.0, width=10.0, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=750.0, width=10.0, opening=5.0, Cd=0.6)

    solver3 = NewtonMultiGridSolver(
        length=1000.0,
        nx=201,
        B=10.0,
        S0=0.001,
        n=0.025,
        structures=[(gate1.position, gate1),
                   (gate2.position, gate2),
                   (gate3.position, gate3)],
        verbose=True
    )

    result3 = solver3.solve_steady_state(Q_target=10.0)

    # 性能对比总结
    print("\n\n" + "=" * 80)
    print("性能对比总结")
    print("=" * 80)

    scenarios = [
        ("无闸门", result1),
        ("单闸门", result2),
        ("三闸门", result3)
    ]

    print(f"{'场景':<15} {'收敛':<8} {'迭代次数':<10} {'残差':<12} {'误差':<12} {'时间(s)':<10}")
    print("-" * 80)

    for name, result in scenarios:
        converged_str = "✓" if result['converged'] else "✗"
        print(f"{name:<15} {converged_str:<8} {result['iterations']:<10} "
              f"{result['residual_norm']:<12.3e} {result['final_error']*100:<11.4f}% "
              f"{result['elapsed_time']:<10.4f}")

    print("=" * 80)


if __name__ == "__main__":
    test_newton_multigrid()
