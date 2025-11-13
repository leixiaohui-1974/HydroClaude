#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


 F(U) = 0


: Claude
: 2025-10-22
"""

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
from typing import Callable, Optional, Tuple, Dict


class NewtonSolver:
    """
    

    
    - U^{k+1} = U^k - J^{-1}·F(U^k)
    - 
    - Jacobian
    - 
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
            linear_solver:  ('direct', 'multigrid')
            max_iter: 
            tol_residual:  ||F(U)|| < tol
            tol_update:  ||ΔU|| < tol
            line_search: 
            verbose: 
        """
        self.linear_solver_type = linear_solver
        self.max_iter = max_iter
        self.tol_residual = tol_residual
        self.tol_update = tol_update
        self.line_search = line_search
        self.verbose = verbose

        # 
        self.mg_solver = None

    def set_multigrid_solver(self, mg_solver):
        """"""
        self.mg_solver = mg_solver
        self.linear_solver_type = 'multigrid'

    def _solve_linear(self, J: csr_matrix, b: np.ndarray,
                     x_init: Optional[np.ndarray] = None) -> np.ndarray:
        """
         J·x = b

        Args:
            J: Jacobian
            b: 
            x_init: 

        Returns:
             x
        """
        if self.linear_solver_type == 'multigrid' and self.mg_solver is not None:
            # 
            x, info = self.mg_solver.solve(J, b, x_init=x_init,
                                           n_cycles=10, tol=1e-10)
            return x
        else:
            # LU
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
        Armijo

         α 
        ||F(U + α·dU)|| ≤ (1 - c·α)·||F(U)||

        Args:
            U: 
            dU: 
            F_current:  F(U)
            residual_func:  F(U)
            max_backtrack: 
            alpha_init: 
            rho: <1
            c: Armijo

        Returns:
             α
        """
        norm_F_current = np.linalg.norm(F_current)
        alpha = alpha_init

        for i in range(max_backtrack):
            U_new = U + alpha * dU
            F_new = residual_func(U_new)
            norm_F_new = np.linalg.norm(F_new)

            # Armijo
            if norm_F_new <= (1 - c * alpha) * norm_F_current:
                if self.verbose and alpha < alpha_init:
                    print(f"    [LineSearch] α={alpha:.3f}, "
                          f"||F||: {norm_F_current:.3e} → {norm_F_new:.3e}")
                return alpha

            # 
            alpha *= rho

        # 
        if self.verbose:
            print(f"    [LineSearch] : α={alpha:.3e}")
        return alpha

    def solve(self,
              U_init: np.ndarray,
              residual_func: Callable[[np.ndarray], np.ndarray],
              jacobian_func: Callable[[np.ndarray], csr_matrix],
              callback: Optional[Callable] = None) -> Tuple[np.ndarray, Dict]:
        """
         F(U) = 0

        Args:
            U_init: 
            residual_func:  F(U)
            jacobian_func: Jacobian J(U) = ∂F/∂U
            callback: 

        Returns:
            U: 
            info: 
                - converged: 
                - iterations: 
                - residual_norm: 
                - residual_history: 
        """
        U = U_init.copy()
        residual_history = []
        update_history = []

        if self.verbose:
            print(f"[Newton] ...")
            print(f"  : {self.linear_solver_type}")
            print(f"  : {'' if self.line_search else ''}")

        for k in range(self.max_iter):
            # Jacobian
            F = residual_func(U)
            J = jacobian_func(U)

            norm_F = np.linalg.norm(F)
            residual_history.append(norm_F)

            # 
            if self.verbose:
                print(f"  Iter {k}: ||F||={norm_F:.3e}")

            # 
            if norm_F < self.tol_residual and k > 0:
                if self.verbose:
                    print(f"  [Newton]  < {self.tol_residual:.1e}")
                return U, {
                    'converged': True,
                    'iterations': k,
                    'residual_norm': norm_F,
                    'residual_history': residual_history,
                    'update_history': update_history,
                    'convergence_reason': 'residual'
                }

            #  J·dU = -F
            try:
                dU_init = np.zeros_like(U) if k == 0 else -dU  # 
                dU = self._solve_linear(J, -F, x_init=dU_init)
            except Exception as e:
                if self.verbose:
                    print(f"  [Newton] : {e}")
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

            # 
            if norm_dU < self.tol_update and k > 0:
                if self.verbose:
                    print(f"  [Newton]  < {self.tol_update:.1e}")
                return U, {
                    'converged': True,
                    'iterations': k,
                    'residual_norm': norm_F,
                    'residual_history': residual_history,
                    'update_history': update_history,
                    'convergence_reason': 'update'
                }

            # 
            if self.line_search:
                alpha = self._line_search(U, dU, F, residual_func)
            else:
                alpha = 1.0

            # 
            U = U + alpha * dU

            # 
            if callback is not None:
                callback(k, U, F, dU, alpha)

        # 
        F_final = residual_func(U)
        norm_F_final = np.linalg.norm(F_final)
        residual_history.append(norm_F_final)

        if self.verbose:
            print(f"  [Newton]  {self.max_iter}")
            print(f"  : {norm_F_final:.3e}")

        return U, {
            'converged': False,
            'iterations': self.max_iter,
            'residual_norm': norm_F_final,
            'residual_history': residual_history,
            'update_history': update_history,
            'convergence_reason': 'max_iterations'
        }


def test_newton_solver():
    """"""
    print("=" * 80)
    print("")
    print("=" * 80)

    # 
    # F1(x, y) = x^2 + y^2 - 1 = 0  
    # F2(x, y) = x - y = 0            x=y
    # (x, y) = (√2/2, √2/2)

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

    # 
    U_init = np.array([0.5, 0.8])

    print(f"\n:  x²+y²=1  x=y ")
    print(f": (√2/2, √2/2) ≈ (0.7071, 0.7071)")
    print(f": ({U_init[0]:.4f}, {U_init[1]:.4f})")

    # 
    print("\n:")
    solver = NewtonSolver(linear_solver='direct',
                         max_iter=20,
                         tol_residual=1e-10,
                         line_search=True,
                         verbose=True)

    U_sol, info = solver.solve(U_init, residual_func, jacobian_func)

    print(f"\n:")
    print(f"  : {info['converged']}")
    print(f"  : {info['iterations']}")
    print(f"  : {info['residual_norm']:.3e}")
    print(f"  : ({U_sol[0]:.10f}, {U_sol[1]:.10f})")

    # 
    exact = np.array([np.sqrt(2)/2, np.sqrt(2)/2])
    error = np.linalg.norm(U_sol - exact)
    print(f"  : {error:.3e}")

    # 
    if len(info['residual_history']) > 3:
        print(f"\n:")
        res_hist = info['residual_history']
        for i in range(1, min(5, len(res_hist))):
            if res_hist[i-1] > 1e-14 and res_hist[i] > 1e-14:
                rate = np.log(res_hist[i]) / np.log(res_hist[i-1])
                print(f"  Iter {i-1}→{i}: {res_hist[i-1]:.3e} → {res_hist[i]:.3e}, "
                      f"rate≈{rate:.2f} (2)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_newton_solver()
