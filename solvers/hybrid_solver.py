#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
混合求解器：迭代法 + 牛顿法

结合迭代法的全局收敛性和牛顿法的局部快速收敛

工作流程：
1. 阶段1：迭代法粗求解（快速到达解的邻域）
2. 阶段2：Newton精细化（快速收敛到高精度）

作者: Claude
日期: 2025-10-22
"""

import numpy as np
import time
from typing import Dict, Tuple, Optional, Callable
from scipy.sparse import spmatrix

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.newton_solver import NewtonSolver


class HybridSolver:
    """
    混合求解器：迭代法 + 牛顿法

    策略：
    - 第一阶段：伪时间步进 + Aitken加速（全局收敛性好）
    - 第二阶段：牛顿法（二次收敛速度快）
    - 自动切换：当残差下降到阈值时切换到Newton
    """

    def __init__(self,
                 # 阶段1：迭代法参数
                 iter_max_iter: int = 1000,
                 iter_tol: float = 0.05,
                 switch_threshold: float = 0.1,
                 iter_min: int = 10,
                 # 阶段2：Newton参数
                 newton_max_iter: int = 20,
                 newton_tol: float = 1e-4,
                 pseudo_dt: float = 0.1,
                 # Aitken加速参数
                 aitken_relax_min: float = 0.1,
                 aitken_relax_max: float = 1.5,
                 # 其他
                 verbose: bool = True):
        """
        初始化混合求解器

        Args:
            iter_max_iter: 迭代法最大迭代次数
            iter_tol: 迭代法收敛容差（相对残差）
            switch_threshold: 切换到Newton的残差阈值（相对残差）
            iter_min: 最少迭代次数（避免过早切换）
            newton_max_iter: Newton最大迭代次数
            newton_tol: Newton收敛容差（绝对残差）
            pseudo_dt: 伪时间步长
            aitken_relax_min: Aitken松弛因子最小值
            aitken_relax_max: Aitken松弛因子最大值
            verbose: 是否输出详细信息
        """
        # 阶段1参数
        self.iter_max_iter = iter_max_iter
        self.iter_tol = iter_tol
        self.switch_threshold = switch_threshold
        self.iter_min = iter_min

        # 阶段2参数
        self.newton_max_iter = newton_max_iter
        self.newton_tol = newton_tol
        self.pseudo_dt = pseudo_dt

        # Aitken参数
        self.aitken_relax_min = aitken_relax_min
        self.aitken_relax_max = aitken_relax_max

        # 其他
        self.verbose = verbose

    def solve(self,
              system,
              U_init: np.ndarray,
              t: float = 0.0) -> Tuple[np.ndarray, Dict]:
        """
        求解非线性系统

        Args:
            system: SteadySaintVenantSystem实例
            U_init: 初值 [h_0, Q_0, h_1, Q_1, ...]
            t: 时间

        Returns:
            U_solution: 解
            info: 求解信息字典
        """
        start_time_total = time.time()

        if self.verbose:
            print("[HybridSolver] 开始混合求解...")
            print(f"  阶段1: 迭代法粗求解 (tol={self.iter_tol}, switch={self.switch_threshold})")
            print(f"  阶段2: Newton精细化 (tol={self.newton_tol})")
            print()

        # 设置系统的伪时间步长
        original_pseudo_dt = system.pseudo_dt
        system.pseudo_dt = self.pseudo_dt

        # 阶段1：迭代法粗求解
        if self.verbose:
            print("=" * 80)
            print("阶段1: 迭代法粗求解")
            print("=" * 80)

        start_time_phase1 = time.time()
        U_phase1, phase1_info = self._solve_iterative_phase(system, U_init, t)
        time_phase1 = time.time() - start_time_phase1

        if self.verbose:
            print(f"  迭代次数: {phase1_info['iterations']}")
            print(f"  最终残差: {phase1_info['final_residual']:.4e}")
            print(f"  相对残差: {phase1_info['relative_residual']:.4e}")
            print(f"  用时: {time_phase1:.4f}s")
            if phase1_info['switched']:
                print(f"  状态: 达到切换阈值，准备切换到Newton")
            elif phase1_info['converged']:
                print(f"  状态: 已收敛到目标精度")
            else:
                print(f"  状态: 达到最大迭代次数")
            print()

        # 阶段2：Newton精细化
        if self.verbose:
            print("=" * 80)
            print("阶段2: Newton精细化")
            print("=" * 80)

        start_time_phase2 = time.time()
        U_solution, phase2_info = self._solve_newton_phase(system, U_phase1, t)
        time_phase2 = time.time() - start_time_phase2

        if self.verbose:
            print(f"  迭代次数: {phase2_info['iterations']}")
            print(f"  最终残差: {phase2_info.get('final_residual_norm', 'N/A')}")
            print(f"  用时: {time_phase2:.4f}s")
            print(f"  状态: {'收敛' if phase2_info['converged'] else '未收敛'}")
            print()

        # 恢复原始pseudo_dt
        system.pseudo_dt = original_pseudo_dt

        time_total = time.time() - start_time_total

        # 汇总信息
        info = {
            'converged': phase2_info['converged'],
            'phase1_iterations': phase1_info['iterations'],
            'phase2_iterations': phase2_info['iterations'],
            'total_iterations': phase1_info['iterations'] + phase2_info['iterations'],
            'phase1_time': time_phase1,
            'phase2_time': time_phase2,
            'total_time': time_total,
            'final_residual': phase2_info.get('final_residual_norm', phase1_info['final_residual']),
            'switched_at_iteration': phase1_info['iterations'] if phase1_info['switched'] else None,
            'phase1_converged': phase1_info['converged'],
            'phase2_converged': phase2_info['converged']
        }

        if self.verbose:
            print("=" * 80)
            print("混合求解完成")
            print("=" * 80)
            print(f"  总迭代次数: {info['total_iterations']} (阶段1: {info['phase1_iterations']}, 阶段2: {info['phase2_iterations']})")
            print(f"  总用时: {info['total_time']:.4f}s (阶段1: {info['phase1_time']:.4f}s, 阶段2: {info['phase2_time']:.4f}s)")
            print(f"  最终状态: {'✅ 收敛' if info['converged'] else '❌ 未收敛'}")
            print()

        return U_solution, info

    def _solve_iterative_phase(self,
                               system,
                               U_init: np.ndarray,
                               t: float) -> Tuple[np.ndarray, Dict]:
        """
        阶段1：迭代法粗求解

        使用伪时间步进 + Aitken自适应松弛

        Returns:
            U: 粗解
            info: 求解信息
        """
        U = U_init.copy()
        U_prev = U.copy()
        U_prev2 = U.copy()

        # Aitken参数
        alpha = 1.0
        alpha_prev = 1.0

        # 初始残差
        system.U_prev = U.copy()
        F0 = system.compute_residual(U, t)
        residual_0 = np.linalg.norm(F0)

        if residual_0 < 1e-12:
            # 初值已经是解
            return U, {
                'iterations': 0,
                'final_residual': residual_0,
                'relative_residual': 0.0,
                'converged': True,
                'switched': False
            }

        converged = False
        switched = False

        for k in range(self.iter_max_iter):
            # 计算残差
            F = system.compute_residual(U, t)
            residual_norm = np.linalg.norm(F)
            relative_residual = residual_norm / residual_0

            if self.verbose and k % 50 == 0:
                print(f"  Iter {k}: ||R||={residual_norm:.4e}, ||R||/||R0||={relative_residual:.4e}, α={alpha:.4f}")

            # 检查是否达到切换阈值
            if k >= self.iter_min and relative_residual < self.switch_threshold:
                switched = True
                if self.verbose:
                    print(f"  达到切换阈值 ({relative_residual:.4e} < {self.switch_threshold})")
                break

            # 检查收敛
            if relative_residual < self.iter_tol:
                converged = True
                if self.verbose:
                    print(f"  迭代法收敛 ({relative_residual:.4e} < {self.iter_tol})")
                break

            # 伪时间步进
            U_new = U - alpha * F * self.pseudo_dt

            # Aitken加速（从第2次迭代开始）
            if k >= 2:
                alpha = self._compute_aitken_alpha(U, U_new, U_prev, U_prev2, alpha_prev)
                alpha = np.clip(alpha, self.aitken_relax_min, self.aitken_relax_max)

            # 更新
            U_prev2 = U_prev.copy()
            U_prev = U.copy()
            alpha_prev = alpha
            U = U_new.copy()

            # 更新系统的U_prev（伪瞬态需要）
            system.U_prev = U.copy()

        info = {
            'iterations': k + 1 if not (converged or switched) else k,
            'final_residual': residual_norm,
            'relative_residual': relative_residual,
            'converged': converged,
            'switched': switched
        }

        return U, info

    def _compute_aitken_alpha(self,
                             U_k: np.ndarray,
                             U_kp1: np.ndarray,
                             U_km1: np.ndarray,
                             U_km2: np.ndarray,
                             alpha_prev: float) -> float:
        """
        计算Aitken自适应松弛因子

        基于连续两次迭代的变化量

        Args:
            U_k: 当前解
            U_kp1: 下一步解（未加速）
            U_km1: 前一步解
            U_km2: 前两步解
            alpha_prev: 前一步松弛因子

        Returns:
            alpha: 新的松弛因子
        """
        # 当前和前一次的迭代增量
        delta_k = U_kp1 - U_k
        delta_km1 = U_k - U_km1

        # 增量的变化
        delta_delta = delta_k - delta_km1

        # Aitken公式
        denominator = np.dot(delta_delta, delta_delta)

        if denominator < 1e-12:
            # 增量几乎不变，保持当前松弛因子
            return alpha_prev

        numerator = -np.dot(delta_km1, delta_delta)
        alpha_aitken = numerator / denominator

        # 保守策略：逐步调整
        alpha_new = 0.5 * alpha_prev + 0.5 * alpha_aitken

        return alpha_new

    def _solve_newton_phase(self,
                           system,
                           U_init: np.ndarray,
                           t: float) -> Tuple[np.ndarray, Dict]:
        """
        阶段2：Newton精细化

        Args:
            system: SteadySaintVenantSystem实例
            U_init: 粗解（来自阶段1）
            t: 时间

        Returns:
            U_solution: 精细解
            info: 求解信息
        """
        # 更新系统的U_prev为阶段1的解
        system.U_prev = U_init.copy()

        # 创建Newton求解器
        newton = NewtonSolver(
            max_iter=self.newton_max_iter,
            tol_residual=self.newton_tol,
            linear_solver='direct',
            line_search=True,
            verbose=self.verbose
        )

        # 求解
        try:
            U_sol, info = newton.solve(
                U_init=U_init,
                residual_func=lambda U: system.compute_residual(U, t),
                jacobian_func=lambda U: system.compute_jacobian(U, t)
            )
            return U_sol, info

        except Exception as e:
            if self.verbose:
                print(f"  ❌ Newton求解失败: {e}")
            # 返回阶段1的解
            return U_init, {
                'converged': False,
                'iterations': 0,
                'final_residual_norm': np.linalg.norm(system.compute_residual(U_init, t))
            }


def main():
    """简单测试"""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from physics.steady_saint_venant import SteadySaintVenantSystem
    from solvers.gate import SluiceGate
    from utils.canal_utils import compute_steady_uniform_flow

    print("=" * 100)
    print("HybridSolver简单测试")
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
        pseudo_dt=0.1
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

    # 混合求解器
    solver = HybridSolver(
        iter_max_iter=1000,
        iter_tol=0.05,
        switch_threshold=0.1,
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


if __name__ == '__main__':
    main()
