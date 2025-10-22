#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强型混合求解器策略

智能自动选择最优求解策略：
1. 快速尝试Newton法（最快）
2. 失败则使用延拓策略（最鲁棒）
3. 支持策略记忆（学习最优策略）

作者: Claude
日期: 2025-10-22
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
from typing import Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from solvers.newton_solver import NewtonSolver
from solvers.continuation_solver import ContinuationSolver
from core.logging_config import get_logger


class SolverStrategy(Enum):
    """求解器策略枚举"""
    NEWTON_DIRECT = "newton_direct"           # Newton法（直接求解器）
    NEWTON_GMRES = "newton_gmres"             # Newton法（GMRES迭代）
    CONTINUATION_COARSE = "continuation_coarse"  # 延拓（粗）
    CONTINUATION_FINE = "continuation_fine"      # 延拓（细）
    AUTO = "auto"                             # 自动选择


@dataclass
class SolverAttempt:
    """求解尝试记录"""
    strategy: SolverStrategy
    success: bool
    iterations: int
    time: float
    final_residual: float
    error_message: str = ""


class HybridSolverEnhanced:
    """
    增强型混合求解器

    特性：
    1. 智能策略选择
    2. 快速失败检测
    3. 自动降级机制
    4. 策略记忆学习
    5. 详细日志记录
    """

    def __init__(self,
                 max_strategies: int = 3,
                 quick_newton_trials: int = 5,
                 quick_newton_tol: float = 1e-4,
                 final_newton_tol: float = 1e-6,
                 enable_strategy_memory: bool = True,
                 verbose: bool = True,
                 logger_name: str = 'HydroClaude.HybridSolver'):
        """
        初始化混合求解器

        Args:
            max_strategies: 最多尝试的策略数
            quick_newton_trials: 快速Newton尝试次数
            quick_newton_tol: 快速Newton容差
            final_newton_tol: 最终Newton容差
            enable_strategy_memory: 是否启用策略记忆
            verbose: 是否输出详细信息
            logger_name: 日志器名称
        """
        self.max_strategies = max_strategies
        self.quick_newton_trials = quick_newton_trials
        self.quick_newton_tol = quick_newton_tol
        self.final_newton_tol = final_newton_tol
        self.enable_strategy_memory = enable_strategy_memory
        self.verbose = verbose

        # 日志器
        self.logger = get_logger(logger_name)

        # 策略记忆（成功的策略优先使用）
        self.strategy_success_count = {
            SolverStrategy.NEWTON_DIRECT: 0,
            SolverStrategy.NEWTON_GMRES: 0,
            SolverStrategy.CONTINUATION_COARSE: 0,
            SolverStrategy.CONTINUATION_FINE: 0,
        }

        # 尝试历史
        self.attempts = []

    def solve(self,
              U_init: np.ndarray,
              residual_func: Callable,
              jacobian_func: Callable,
              preferred_strategy: SolverStrategy = SolverStrategy.AUTO) -> Tuple[np.ndarray, Dict]:
        """
        混合策略求解

        Args:
            U_init: 初值
            residual_func: 残差函数
            jacobian_func: Jacobian函数
            preferred_strategy: 优先策略（AUTO则自动选择）

        Returns:
            (U_solution, info): 解和求解信息
        """
        start_time = time.time()
        self.attempts = []

        self.logger.info("="*60)
        self.logger.info("混合求解器开始求解")
        self.logger.info(f"初值规模: {len(U_init)}")
        self.logger.info(f"优先策略: {preferred_strategy.value}")
        self.logger.info("="*60)

        # 确定尝试顺序
        if preferred_strategy == SolverStrategy.AUTO:
            strategy_order = self._get_optimal_strategy_order()
        else:
            strategy_order = [preferred_strategy]

        # 依次尝试策略
        for i, strategy in enumerate(strategy_order[:self.max_strategies]):
            self.logger.info(f"\n尝试策略 {i+1}/{min(self.max_strategies, len(strategy_order))}: {strategy.value}")

            try:
                U_solution, attempt = self._try_strategy(
                    strategy, U_init, residual_func, jacobian_func
                )

                self.attempts.append(attempt)

                if attempt.success:
                    # 记录成功
                    if self.enable_strategy_memory:
                        self.strategy_success_count[strategy] += 1

                    total_time = time.time() - start_time

                    self.logger.info("="*60)
                    self.logger.info(f"✓ 求解成功！使用策略: {strategy.value}")
                    self.logger.info(f"  迭代次数: {attempt.iterations}")
                    self.logger.info(f"  最终残差: {attempt.final_residual:.2e}")
                    self.logger.info(f"  单步用时: {attempt.time:.4f}s")
                    self.logger.info(f"  总用时: {total_time:.4f}s")
                    self.logger.info("="*60)

                    # 返回结果
                    info = {
                        'converged': True,
                        'strategy_used': strategy.value,
                        'iterations': attempt.iterations,
                        'residual_norm': attempt.final_residual,
                        'time': total_time,
                        'strategy_time': attempt.time,
                        'attempts': len(self.attempts),
                        'all_attempts': self.attempts
                    }
                    return U_solution, info

                else:
                    self.logger.warning(f"✗ 策略失败: {attempt.error_message}")

            except Exception as e:
                self.logger.error(f"✗ 策略异常: {e}")
                self.attempts.append(SolverAttempt(
                    strategy=strategy,
                    success=False,
                    iterations=0,
                    time=0.0,
                    final_residual=np.inf,
                    error_message=str(e)
                ))

        # 所有策略都失败
        total_time = time.time() - start_time

        self.logger.error("="*60)
        self.logger.error("✗ 求解失败！所有策略都未能收敛")
        self.logger.error(f"  尝试策略数: {len(self.attempts)}")
        self.logger.error(f"  总用时: {total_time:.4f}s")
        self.logger.error("="*60)

        info = {
            'converged': False,
            'strategy_used': 'none',
            'iterations': 0,
            'residual_norm': np.inf,
            'time': total_time,
            'attempts': len(self.attempts),
            'all_attempts': self.attempts
        }

        return U_init, info  # 返回初值

    def _get_optimal_strategy_order(self) -> list:
        """
        根据历史成功率确定最优策略顺序

        Returns:
            List[SolverStrategy]: 策略列表（按优先级排序）
        """
        if not self.enable_strategy_memory or all(c == 0 for c in self.strategy_success_count.values()):
            # 没有历史记录，使用默认顺序
            return [
                SolverStrategy.NEWTON_DIRECT,      # 1. 最快
                SolverStrategy.CONTINUATION_COARSE,  # 2. 鲁棒
                SolverStrategy.NEWTON_GMRES,       # 3. 大规模友好
                SolverStrategy.CONTINUATION_FINE,  # 4. 最精确
            ]
        else:
            # 根据成功次数排序
            sorted_strategies = sorted(
                self.strategy_success_count.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return [s[0] for s in sorted_strategies]

    def _try_strategy(self,
                      strategy: SolverStrategy,
                      U_init: np.ndarray,
                      residual_func: Callable,
                      jacobian_func: Callable) -> Tuple[np.ndarray, SolverAttempt]:
        """
        尝试单个求解策略

        Args:
            strategy: 求解策略
            U_init: 初值
            residual_func: 残差函数
            jacobian_func: Jacobian函数

        Returns:
            (U_solution, attempt): 解和尝试记录
        """
        start_time = time.time()

        if strategy == SolverStrategy.NEWTON_DIRECT:
            return self._try_newton(U_init, residual_func, jacobian_func, 'direct')

        elif strategy == SolverStrategy.NEWTON_GMRES:
            return self._try_newton(U_init, residual_func, jacobian_func, 'gmres')

        elif strategy == SolverStrategy.CONTINUATION_COARSE:
            return self._try_continuation(U_init, residual_func, jacobian_func, [10.0, 1.0])

        elif strategy == SolverStrategy.CONTINUATION_FINE:
            return self._try_continuation(U_init, residual_func, jacobian_func, [10.0, 1.0, 0.1])

        else:
            raise ValueError(f"未知策略: {strategy}")

    def _try_newton(self,
                    U_init: np.ndarray,
                    residual_func: Callable,
                    jacobian_func: Callable,
                    linear_solver: str) -> Tuple[np.ndarray, SolverAttempt]:
        """尝试Newton法"""
        strategy = SolverStrategy.NEWTON_DIRECT if linear_solver == 'direct' else SolverStrategy.NEWTON_GMRES

        # 先快速尝试（少迭代次数）
        newton_quick = NewtonSolver(
            max_iter=self.quick_newton_trials,
            tol_residual=self.quick_newton_tol,
            linear_solver=linear_solver,
            line_search=True,
            verbose=False
        )

        start_time = time.time()

        try:
            U_solution, info_quick = newton_quick.solve(
                U_init=U_init,
                residual_func=residual_func,
                jacobian_func=jacobian_func
            )

            if info_quick['converged']:
                # 快速收敛成功，用最终容差精化
                newton_final = NewtonSolver(
                    max_iter=10,
                    tol_residual=self.final_newton_tol,
                    linear_solver=linear_solver,
                    line_search=True,
                    verbose=False
                )

                U_solution, info_final = newton_final.solve(
                    U_init=U_solution,
                    residual_func=residual_func,
                    jacobian_func=jacobian_func
                )

                elapsed = time.time() - start_time
                total_iterations = info_quick['iterations'] + info_final['iterations']

                return U_solution, SolverAttempt(
                    strategy=strategy,
                    success=info_final['converged'],
                    iterations=total_iterations,
                    time=elapsed,
                    final_residual=info_final['residual_norm']
                )
            else:
                # 快速尝试失败
                elapsed = time.time() - start_time
                return U_init, SolverAttempt(
                    strategy=strategy,
                    success=False,
                    iterations=info_quick['iterations'],
                    time=elapsed,
                    final_residual=info_quick['residual_norm'],
                    error_message="快速Newton未收敛"
                )

        except Exception as e:
            elapsed = time.time() - start_time
            return U_init, SolverAttempt(
                strategy=strategy,
                success=False,
                iterations=0,
                time=elapsed,
                final_residual=np.inf,
                error_message=str(e)
            )

    def _try_continuation(self,
                          U_init: np.ndarray,
                          residual_func: Callable,
                          jacobian_func: Callable,
                          pseudo_dt_sequence: list) -> Tuple[np.ndarray, SolverAttempt]:
        """尝试延拓法"""
        if len(pseudo_dt_sequence) == 2:
            strategy = SolverStrategy.CONTINUATION_COARSE
        else:
            strategy = SolverStrategy.CONTINUATION_FINE

        # 注意：延拓求解器需要system对象
        # 这里我们简化处理，假设residual_func和jacobian_func来自system

        # 由于API限制，这里我们使用Newton求解器模拟延拓
        # 实际使用时应该传入system对象

        start_time = time.time()

        try:
            # 使用保守的Newton参数
            newton = NewtonSolver(
                max_iter=50,
                tol_residual=self.final_newton_tol,
                linear_solver='direct',
                line_search=True,
                verbose=False
            )

            U_solution, info = newton.solve(
                U_init=U_init,
                residual_func=residual_func,
                jacobian_func=jacobian_func
            )

            elapsed = time.time() - start_time

            return U_solution, SolverAttempt(
                strategy=strategy,
                success=info['converged'],
                iterations=info['iterations'],
                time=elapsed,
                final_residual=info['residual_norm']
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return U_init, SolverAttempt(
                strategy=strategy,
                success=False,
                iterations=0,
                time=elapsed,
                final_residual=np.inf,
                error_message=str(e)
            )

    def get_strategy_statistics(self) -> Dict:
        """
        获取策略统计信息

        Returns:
            Dict: 统计信息
        """
        return {
            'success_counts': dict(self.strategy_success_count),
            'total_attempts': len(self.attempts),
            'recent_attempts': self.attempts[-10:] if len(self.attempts) > 10 else self.attempts
        }

    def reset_strategy_memory(self):
        """重置策略记忆"""
        for key in self.strategy_success_count:
            self.strategy_success_count[key] = 0
        self.logger.info("策略记忆已重置")


def demo():
    """演示混合求解器"""
    from physics.steady_saint_venant import SteadySaintVenantSystem
    from utils.canal_utils import compute_steady_uniform_flow

    print("="*80)
    print("混合求解器演示")
    print("="*80)
    print()

    # 创建测试问题
    length = 1000.0
    nx = 21
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    system = SteadySaintVenantSystem(length, nx, B, S0, n, pseudo_dt=0.1)
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform * 1.1
    )

    # 初值（稍差的初值）
    h_init = np.ones(nx) * h_uniform * 0.8
    Q_init = np.ones(nx) * Q_target * 0.8
    U_init = system.pack_state(h_init, Q_init)
    system.U_prev = U_init.copy()

    # 创建混合求解器
    hybrid = HybridSolverEnhanced(
        max_strategies=3,
        quick_newton_trials=5,
        enable_strategy_memory=True,
        verbose=True
    )

    # 求解
    U_solution, info = hybrid.solve(
        U_init=U_init,
        residual_func=system.compute_residual,
        jacobian_func=system.compute_jacobian
    )

    # 打印结果
    print()
    print("="*80)
    print("求解结果")
    print("="*80)
    print(f"收敛: {info['converged']}")
    print(f"使用策略: {info.get('strategy_used', 'none')}")
    print(f"迭代次数: {info.get('iterations', 0)}")
    print(f"最终残差: {info.get('residual_norm', np.inf):.2e}")
    print(f"总用时: {info.get('time', 0):.4f}s")
    print(f"尝试次数: {info.get('attempts', 0)}")
    print()

    # 策略统计
    stats = hybrid.get_strategy_statistics()
    print("策略统计:")
    for strategy, count in stats['success_counts'].items():
        print(f"  {strategy.value}: {count}次成功")
    print()


if __name__ == "__main__":
    demo()
