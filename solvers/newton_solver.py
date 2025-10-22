#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
牛顿法求解器

用于求解非线性系统 F(U) = 0
支持阻尼牛顿法（线搜索）、自适应步长

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
from typing import Callable, Optional, Tuple, Dict


class NewtonSolver:
    """
    牛顿法求解器

    特点：
    - 经典牛顿法：U^{k+1} = U^k - J^{-1}·F(U^k)
    - 阻尼牛顿法（线搜索）：防止发散
    - 支持稀疏Jacobian
    - 可插拔线性求解器（直接法、多网格等）
    """

    def __init__(self,
                 linear_solver: str = 'direct',
                 max_iter: int = 50,
                 tol_residual: float = 1e-6,
                 tol_update: float = 1e-8,
                 line_search: bool = True,
                 verbose: bool = False):
        """
        Args:
            linear_solver: 线性求解器类型 ('direct', 'multigrid')
            max_iter: 最大牛顿迭代次数
            tol_residual: 残差容差 ||F(U)|| < tol
            tol_update: 更新容差 ||ΔU|| < tol
            line_search: 是否使用线搜索（阻尼牛顿法）
            verbose: 是否输出调试信息
        """
        self.linear_solver_type = linear_solver
        self.max_iter = max_iter
        self.tol_residual = tol_residual
        self.tol_update = tol_update
        self.line_search = line_search
        self.verbose = verbose

        # 可选的多网格求解器（延迟初始化）
        self.mg_solver = None

    def set_multigrid_solver(self, mg_solver):
        """设置多网格求解器（外部注入）"""
        self.mg_solver = mg_solver
        self.linear_solver_type = 'multigrid'

    def _solve_linear(self, J: csr_matrix, b: np.ndarray,
                     x_init: Optional[np.ndarray] = None) -> np.ndarray:
        """
        求解线性系统 J·x = b

        Args:
            J: Jacobian矩阵（稀疏）
            b: 右端项
            x_init: 初始解（多网格使用）

        Returns:
            解向量 x
        """
        if self.linear_solver_type == 'multigrid' and self.mg_solver is not None:
            # 使用多网格求解器
            x, info = self.mg_solver.solve(J, b, x_init=x_init,
                                           n_cycles=10, tol=1e-10)
            return x
        else:
            # 直接求解（稀疏LU）
            return spsolve(J, b)

    def _line_search(self,
                     U: np.ndarray,
                     dU: np.ndarray,
                     F_current: np.ndarray,
                     residual_func: Callable,
                     max_backtrack: int = 10,
                     alpha_init: float = 1.0,
                     rho: float = 0.5,
                     c: float = 1e-4) -> float:
        """
        回溯线搜索（Armijo准则）

        寻找步长 α 使得：
        ||F(U + α·dU)|| ≤ (1 - c·α)·||F(U)||

        Args:
            U: 当前解
            dU: 牛顿方向
            F_current: 当前残差 F(U)
            residual_func: 残差函数 F(U)
            max_backtrack: 最大回溯次数
            alpha_init: 初始步长
            rho: 回溯因子（<1）
            c: Armijo参数

        Returns:
            步长 α
        """
        norm_F_current = np.linalg.norm(F_current)
        alpha = alpha_init

        for i in range(max_backtrack):
            U_new = U + alpha * dU
            F_new = residual_func(U_new)
            norm_F_new = np.linalg.norm(F_new)

            # Armijo条件
            if norm_F_new <= (1 - c * alpha) * norm_F_current:
                if self.verbose and alpha < alpha_init:
                    print(f"    [LineSearch] α={alpha:.3f}, "
                          f"||F||: {norm_F_current:.3e} → {norm_F_new:.3e}")
                return alpha

            # 回溯
            alpha *= rho

        # 如果所有步长都不满足，返回最小步长
        if self.verbose:
            print(f"    [LineSearch] 警告: 达到最大回溯次数，使用α={alpha:.3e}")
        return alpha

    def solve(self,
              U_init: np.ndarray,
              residual_func: Callable[[np.ndarray], np.ndarray],
              jacobian_func: Callable[[np.ndarray], csr_matrix],
              callback: Optional[Callable] = None) -> Tuple[np.ndarray, Dict]:
        """
        牛顿法求解 F(U) = 0

        Args:
            U_init: 初始解
            residual_func: 残差函数 F(U)
            jacobian_func: Jacobian函数 J(U) = ∂F/∂U
            callback: 回调函数（每次迭代后调用）

        Returns:
            U: 解向量
            info: 求解信息字典
                - converged: 是否收敛
                - iterations: 迭代次数
                - residual_norm: 最终残差范数
                - residual_history: 残差历史
        """
        U = U_init.copy()
        residual_history = []
        update_history = []

        if self.verbose:
            print(f"[Newton] 开始牛顿迭代...")
            print(f"  线性求解器: {self.linear_solver_type}")
            print(f"  线搜索: {'启用' if self.line_search else '禁用'}")

        for k in range(self.max_iter):
            # 计算残差和Jacobian
            F = residual_func(U)
            J = jacobian_func(U)

            norm_F = np.linalg.norm(F)
            residual_history.append(norm_F)

            # 打印进度
            if self.verbose:
                print(f"  Iter {k}: ||F||={norm_F:.3e}")

            # 检查收敛（残差）
            if norm_F < self.tol_residual and k > 0:
                if self.verbose:
                    print(f"  [Newton] 收敛（残差 < {self.tol_residual:.1e}）")
                return U, {
                    'converged': True,
                    'iterations': k,
                    'residual_norm': norm_F,
                    'residual_history': residual_history,
                    'update_history': update_history,
                    'convergence_reason': 'residual'
                }

            # 求解线性系统 J·dU = -F
            try:
                dU_init = np.zeros_like(U) if k == 0 else -dU  # 使用上次结果作为初值
                dU = self._solve_linear(J, -F, x_init=dU_init)
            except Exception as e:
                if self.verbose:
                    print(f"  [Newton] 线性求解失败: {e}")
                return U, {
                    'converged': False,
                    'iterations': k,
                    'residual_norm': norm_F,
                    'residual_history': residual_history,
                    'update_history': update_history,
                    'convergence_reason': 'linear_solver_failure'
                }

            norm_dU = np.linalg.norm(dU)
            update_history.append(norm_dU)

            # 检查收敛（更新）
            if norm_dU < self.tol_update and k > 0:
                if self.verbose:
                    print(f"  [Newton] 收敛（更新 < {self.tol_update:.1e}）")
                return U, {
                    'converged': True,
                    'iterations': k,
                    'residual_norm': norm_F,
                    'residual_history': residual_history,
                    'update_history': update_history,
                    'convergence_reason': 'update'
                }

            # 线搜索
            if self.line_search:
                alpha = self._line_search(U, dU, F, residual_func)
            else:
                alpha = 1.0

            # 更新解
            U = U + alpha * dU

            # 回调
            if callback is not None:
                callback(k, U, F, dU, alpha)

        # 未收敛
        F_final = residual_func(U)
        norm_F_final = np.linalg.norm(F_final)
        residual_history.append(norm_F_final)

        if self.verbose:
            print(f"  [Newton] 未收敛（达到最大迭代次数 {self.max_iter}）")
            print(f"  最终残差: {norm_F_final:.3e}")

        return U, {
            'converged': False,
            'iterations': self.max_iter,
            'residual_norm': norm_F_final,
            'residual_history': residual_history,
            'update_history': update_history,
            'convergence_reason': 'max_iterations'
        }


def test_newton_solver():
    """测试牛顿求解器"""
    print("=" * 80)
    print("牛顿求解器测试")
    print("=" * 80)

    # 测试问题：非线性方程组
    # F1(x, y) = x^2 + y^2 - 1 = 0  （单位圆）
    # F2(x, y) = x - y = 0           （直线 x=y）
    # 解析解：(x, y) = (√2/2, √2/2)

    def residual_func(U):
        x, y = U
        F1 = x**2 + y**2 - 1
        F2 = x - y
        return np.array([F1, F2])

    def jacobian_func(U):
        x, y = U
        J = np.array([[2*x, 2*y],
                     [1, -1]])
        return csr_matrix(J)

    # 初始解
    U_init = np.array([0.5, 0.8])

    print(f"\n问题: 求解圆 x²+y²=1 与直线 x=y 的交点")
    print(f"解析解: (√2/2, √2/2) ≈ (0.7071, 0.7071)")
    print(f"初始解: ({U_init[0]:.4f}, {U_init[1]:.4f})")

    # 测试牛顿求解器
    print("\n牛顿求解器（带线搜索）:")
    solver = NewtonSolver(linear_solver='direct',
                         max_iter=20,
                         tol_residual=1e-10,
                         line_search=True,
                         verbose=True)

    U_sol, info = solver.solve(U_init, residual_func, jacobian_func)

    print(f"\n结果:")
    print(f"  收敛: {info['converged']}")
    print(f"  迭代次数: {info['iterations']}")
    print(f"  最终残差: {info['residual_norm']:.3e}")
    print(f"  解: ({U_sol[0]:.10f}, {U_sol[1]:.10f})")

    # 验证
    exact = np.array([np.sqrt(2)/2, np.sqrt(2)/2])
    error = np.linalg.norm(U_sol - exact)
    print(f"  误差: {error:.3e}")

    # 检查收敛速率
    if len(info['residual_history']) > 3:
        print(f"\n收敛速率分析:")
        res_hist = info['residual_history']
        for i in range(1, min(5, len(res_hist))):
            if res_hist[i-1] > 1e-14 and res_hist[i] > 1e-14:
                rate = np.log(res_hist[i]) / np.log(res_hist[i-1])
                print(f"  Iter {i-1}→{i}: {res_hist[i-1]:.3e} → {res_hist[i]:.3e}, "
                      f"rate≈{rate:.2f} (接近2为二次收敛)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_newton_solver()
