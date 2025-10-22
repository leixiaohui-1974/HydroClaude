#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
延拓求解器：伪时间步长延拓 + 牛顿法

策略：逐步减小pseudo_dt，每个阶段用Newton求解
- 大pseudo_dt: Jacobian更对角占优，更稳定（容易求解）
- 小pseudo_dt: 接近真实稳态方程（高精度解）

作者: Claude
日期: 2025-10-22
"""

import numpy as np
import time
from typing import Dict, Tuple, List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.newton_solver import NewtonSolver


class ContinuationSolver:
    """
    延拓求解器：伪时间步长延拓

    工作流程：
    1. pseudo_dt = 10.0 → Newton求解（粗解）
    2. pseudo_dt = 1.0  → Newton求解（中等精度）
    3. pseudo_dt = 0.1  → Newton求解（高精度）
    """

    def __init__(self,
                 pseudo_dt_sequence: List[float] = None,
                 newton_max_iter: int = 20,
                 newton_tol: float = 1e-4,
                 verbose: bool = True):
        """
        初始化延拓求解器

        Args:
            pseudo_dt_sequence: 伪时间步长序列（从大到小）
            newton_max_iter: 每个阶段Newton最大迭代次数
            newton_tol: Newton收敛容差
            verbose: 是否输出详细信息
        """
        # 默认延拓序列：10.0 → 1.0 → 0.1
        self.pseudo_dt_sequence = pseudo_dt_sequence or [10.0, 1.0, 0.1]
        self.newton_max_iter = newton_max_iter
        self.newton_tol = newton_tol
        self.verbose = verbose

    def solve(self,
              system,
              U_init: np.ndarray,
              t: float = 0.0) -> Tuple[np.ndarray, Dict]:
        """
        求解非线性系统

        Args:
            system: SteadySaintVenantSystem实例
            U_init: 初值
            t: 时间

        Returns:
            U_solution: 解
            info: 求解信息
        """
        start_time_total = time.time()

        if self.verbose:
            print("[ContinuationSolver] 开始延拓求解...")
            print(f"  pseudo_dt序列: {self.pseudo_dt_sequence}")
            print(f"  Newton参数: max_iter={self.newton_max_iter}, tol={self.newton_tol}")
            print()

        # 保存原始pseudo_dt
        original_pseudo_dt = system.pseudo_dt

        U_current = U_init.copy()
        all_stage_info = []

        # 逐阶段求解
        for stage, pseudo_dt in enumerate(self.pseudo_dt_sequence):
            if self.verbose:
                print("=" * 80)
                print(f"阶段 {stage + 1}/{len(self.pseudo_dt_sequence)}: pseudo_dt = {pseudo_dt}")
                print("=" * 80)

            # 设置系统的pseudo_dt
            system.pseudo_dt = pseudo_dt

            # 更新U_prev
            system.U_prev = U_current.copy()

            # Newton求解
            newton = NewtonSolver(
                max_iter=self.newton_max_iter,
                tol_residual=self.newton_tol,
                linear_solver='direct',
                line_search=True,
                verbose=self.verbose
            )

            start_time_stage = time.time()
            try:
                U_current, stage_info = newton.solve(
                    U_init=U_current,
                    residual_func=lambda U: system.compute_residual(U, t),
                    jacobian_func=lambda U: system.compute_jacobian(U, t)
                )
                time_stage = time.time() - start_time_stage

                stage_info['pseudo_dt'] = pseudo_dt
                stage_info['time'] = time_stage
                all_stage_info.append(stage_info)

                if self.verbose:
                    print(f"  阶段{stage + 1}完成: {'✅ 收敛' if stage_info['converged'] else '❌ 未收敛'}")
                    print(f"  迭代次数: {stage_info['iterations']}")
                    print(f"  用时: {time_stage:.4f}s")
                    print()

                # 如果未收敛，停止延拓
                if not stage_info['converged']:
                    if self.verbose:
                        print(f"⚠️ 阶段{stage + 1}未收敛，停止延拓")
                    break

            except Exception as e:
                if self.verbose:
                    print(f"  ❌ 阶段{stage + 1}求解失败: {e}")
                break

        # 恢复原始pseudo_dt
        system.pseudo_dt = original_pseudo_dt

        time_total = time.time() - start_time_total

        # 汇总信息
        total_iterations = sum(s['iterations'] for s in all_stage_info)
        final_converged = all_stage_info[-1]['converged'] if all_stage_info else False

        info = {
            'converged': final_converged,
            'total_iterations': total_iterations,
            'total_time': time_total,
            'num_stages': len(all_stage_info),
            'stage_info': all_stage_info
        }

        if self.verbose:
            print("=" * 80)
            print("延拓求解完成")
            print("=" * 80)
            print(f"  完成阶段数: {len(all_stage_info)}/{len(self.pseudo_dt_sequence)}")
            print(f"  总迭代次数: {total_iterations}")
            print(f"  总用时: {time_total:.4f}s")
            print(f"  最终状态: {'✅ 收敛' if final_converged else '❌ 未收敛'}")
            print()

        return U_current, info


def main():
    """测试延拓求解器"""
    from physics.steady_saint_venant import SteadySaintVenantSystem
    from solvers.gate import SluiceGate
    from utils.canal_utils import compute_steady_uniform_flow

    print("=" * 100)
    print("延拓求解器测试 - 三闸门")
    print("=" * 100)
    print()

    # 三闸门场景
    length = 10000.0
    nx = 301
    B = 10.0
    S0 = 0.0005
    n = 0.025
    Q_target = 10.0

    gate1 = SluiceGate(position=2500.0, width=B, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=B, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=B, opening=5.0, Cd=0.6)

    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    print(f"场景: 三闸门")
    print(f"  网格: {nx}点, {length}m")
    print(f"  流量: {Q_target} m³/s")
    print(f"  均匀流水深: {h_uniform:.4f} m")
    print()

    # 创建系统
    system = SteadySaintVenantSystem(
        length, nx, B, S0, n,
        structures=[
            (gate1.position, gate1),
            (gate2.position, gate2),
            (gate3.position, gate3)
        ],
        pseudo_dt=0.1  # 这个会被延拓求解器覆盖
    )
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform
    )

    # 初值（均匀流）
    h_init = np.ones(nx) * h_uniform
    Q_init = np.ones(nx) * Q_target
    U_init = system.pack_state(h_init, Q_init)
    system.U_prev = U_init.copy()

    # 延拓求解器
    solver = ContinuationSolver(
        pseudo_dt_sequence=[10.0, 1.0, 0.1],
        newton_max_iter=20,
        newton_tol=1e-4,
        verbose=True
    )

    U_sol, info = solver.solve(system, U_init, t=0.0)

    # 解析结果
    h_sol, Q_sol = system.unpack_state(U_sol)

    print("=" * 100)
    print("求解结果")
    print("=" * 100)
    print(f"  收敛: {'✅' if info['converged'] else '❌'}")
    print(f"  总迭代次数: {info['total_iterations']}")
    print(f"  总用时: {info['total_time']:.4f}s")
    print(f"  水深范围: {h_sol.min():.4f} - {h_sol.max():.4f} m")
    print(f"  流量范围: {Q_sol.min():.4f} - {Q_sol.max():.4f} m³/s")
    print()

    # 各阶段详情
    print("各阶段详情:")
    for i, stage in enumerate(info['stage_info']):
        print(f"  阶段{i+1} (pseudo_dt={stage['pseudo_dt']}): "
              f"{stage['iterations']}次迭代, {stage['time']:.4f}s")
    print()


if __name__ == '__main__':
    main()
