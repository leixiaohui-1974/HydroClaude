#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 + 




1. 1
2. 2Newton

: Claude
: 2025-10-22
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
     + 

    
    -  + Aitken
    - 
    - Newton
    """

    def __init__(self,
                 # 1
                 iter_max_iter: int = 1000,
                 iter_tol: float = 0.05,
                 switch_threshold: float = 0.1,
                 iter_min: int = 10,
                 # 2Newton
                 newton_max_iter: int = 20,
                 newton_tol: float = 1e-4,
                 pseudo_dt: float = 0.1,
                 # Aitken
                 aitken_relax_min: float = 0.1,
                 aitken_relax_max: float = 1.5,
                 # 
                 verbose: bool = True):
        """
        

        Args:
            iter_max_iter: 
            iter_tol: 
            switch_threshold: Newton
            iter_min: 
            newton_max_iter: Newton
            newton_tol: Newton
            pseudo_dt: 
            aitken_relax_min: Aitken
            aitken_relax_max: Aitken
            verbose: 
        """
        # 1
        self.iter_max_iter = iter_max_iter
        self.iter_tol = iter_tol
        self.switch_threshold = switch_threshold
        self.iter_min = iter_min

        # 2
        self.newton_max_iter = newton_max_iter
        self.newton_tol = newton_tol
        self.pseudo_dt = pseudo_dt

        # Aitken
        self.aitken_relax_min = aitken_relax_min
        self.aitken_relax_max = aitken_relax_max

        # 
        self.verbose = verbose

    def solve(self,
              system,
              U_init: np.ndarray,
              t: float = 0.0) -> Tuple[np.ndarray, Dict]:
        """
        

        Args:
            system: SteadySaintVenantSystem
            U_init:  [h_0, Q_0, h_1, Q_1, ...]
            t: 

        Returns:
            U_solution: 
            info: 
        """
        start_time_total = time.time()

        if self.verbose:
            print("[HybridSolver] ...")
            print(f"  1:  (tol={self.iter_tol}, switch={self.switch_threshold})")
            print(f"  2: Newton (tol={self.newton_tol})")
            print()

        # 
        original_pseudo_dt = system.pseudo_dt
        system.pseudo_dt = self.pseudo_dt

        # 1
        if self.verbose:
            print("=" * 80)
            print("1: ")
            print("=" * 80)

        start_time_phase1 = time.time()
        U_phase1, phase1_info = self._solve_iterative_phase(system, U_init, t)
        time_phase1 = time.time() - start_time_phase1

        if self.verbose:
            print(f"  : {phase1_info['iterations']}")
            print(f"  : {phase1_info['final_residual']:.4e}")
            print(f"  : {phase1_info['relative_residual']:.4e}")
            print(f"  : {time_phase1:.4f}s")
            if phase1_info['switched']:
                print(f"  : Newton")
            elif phase1_info['converged']:
                print(f"  : ")
            else:
                print(f"  : ")
            print()

        # 2Newton
        if self.verbose:
            print("=" * 80)
            print("2: Newton")
            print("=" * 80)

        start_time_phase2 = time.time()
        U_solution, phase2_info = self._solve_newton_phase(system, U_phase1, t)
        time_phase2 = time.time() - start_time_phase2

        if self.verbose:
            print(f"  : {phase2_info['iterations']}")
            print(f"  : {phase2_info.get('final_residual_norm', 'N/A')}")
            print(f"  : {time_phase2:.4f}s")
            print(f"  : {'' if phase2_info['converged'] else ''}")
            print()

        # pseudo_dt
        system.pseudo_dt = original_pseudo_dt

        time_total = time.time() - start_time_total

        # 
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
            print("")
            print("=" * 80)
            print(f"  : {info['total_iterations']} (1: {info['phase1_iterations']}, 2: {info['phase2_iterations']})")
            print(f"  : {info['total_time']:.4f}s (1: {info['phase1_time']:.4f}s, 2: {info['phase2_time']:.4f}s)")
            print(f"  : {' ' if info['converged'] else ' '}")
            print()

        return U_solution, info

    def _solve_iterative_phase(self,
                               system,
                               U_init: np.ndarray,
                               t: float) -> Tuple[np.ndarray, Dict]:
        """
        1

         + Aitken

        Returns:
            U: 
            info: 
        """
        U = U_init.copy()
        U_prev = U.copy()
        U_prev2 = U.copy()

        # Aitken
        alpha = 1.0
        alpha_prev = 1.0

        # 
        system.U_prev = U.copy()
        F0 = system.compute_residual(U, t)
        residual_0 = np.linalg.norm(F0)

        if residual_0 < 1e-12:
            # 
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
            # 
            F = system.compute_residual(U, t)
            residual_norm = np.linalg.norm(F)
            relative_residual = residual_norm / residual_0

            if self.verbose and k % 50 == 0:
                print(f"  Iter {k}: ||R||={residual_norm:.4e}, ||R||/||R0||={relative_residual:.4e}, α={alpha:.4f}")

            # 
            if k >= self.iter_min and relative_residual < self.switch_threshold:
                switched = True
                if self.verbose:
                    print(f"   ({relative_residual:.4e} < {self.switch_threshold})")
                break

            # 
            if relative_residual < self.iter_tol:
                converged = True
                if self.verbose:
                    print(f"   ({relative_residual:.4e} < {self.iter_tol})")
                break

            # 
            U_new = U - alpha * F * self.pseudo_dt

            # Aitken2
            if k >= 2:
                alpha = self._compute_aitken_alpha(U, U_new, U_prev, U_prev2, alpha_prev)
                alpha = np.clip(alpha, self.aitken_relax_min, self.aitken_relax_max)

            # 
            U_prev2 = U_prev.copy()
            U_prev = U.copy()
            alpha_prev = alpha
            U = U_new.copy()

            # U_prev
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
        Aitken

        

        Args:
            U_k: 
            U_kp1: 
            U_km1: 
            U_km2: 
            alpha_prev: 

        Returns:
            alpha: 
        """
        # 
        delta_k = U_kp1 - U_k
        delta_km1 = U_k - U_km1

        # 
        delta_delta = delta_k - delta_km1

        # Aitken
        denominator = np.dot(delta_delta, delta_delta)

        if denominator < 1e-12:
            # 
            return alpha_prev

        numerator = -np.dot(delta_km1, delta_delta)
        alpha_aitken = numerator / denominator

        # 
        alpha_new = 0.5 * alpha_prev + 0.5 * alpha_aitken

        return alpha_new

    def _solve_newton_phase(self,
                           system,
                           U_init: np.ndarray,
                           t: float) -> Tuple[np.ndarray, Dict]:
        """
        2Newton

        Args:
            system: SteadySaintVenantSystem
            U_init: 1
            t: 

        Returns:
            U_solution: 
            info: 
        """
        # U_prev1
        system.U_prev = U_init.copy()

        # Newton
        newton = NewtonSolver(
            max_iter=self.newton_max_iter,
            tol_residual=self.newton_tol,
            linear_solver='direct',
            line_search=True,
            verbose=self.verbose
        )

        # 
        try:
            U_sol, info = newton.solve(
                U_init=U_init,
                residual_func=lambda U: system.compute_residual(U, t),
                jacobian_func=lambda U: system.compute_jacobian(U, t)
            )
            return U_sol, info

        except Exception as e:
            if self.verbose:
                print(f"   Newton: {e}")
            # 1
            return U_init, {
                'converged': False,
                'iterations': 0,
                'final_residual_norm': np.linalg.norm(system.compute_residual(U_init, t))
            }


def main():
    """"""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from physics.steady_saint_venant import SteadySaintVenantSystem
    from solvers.gate import SluiceGate
    from utils.canal_utils import compute_steady_uniform_flow

    print("=" * 100)
    print("HybridSolver")
    print("=" * 100)
    print()

    # 
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

    print(f": ")
    print(f"  : {nx}, {length}m")
    print(f"  : {Q_target} m³/s")
    print(f"  : {h_uniform:.4f} m")
    print()

    # 
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

    # 
    h_init = np.ones(nx) * h_uniform
    Q_init = np.ones(nx) * Q_target
    U_init = system.pack_state(h_init, Q_init)
    system.U_prev = U_init.copy()

    # 
    solver = HybridSolver(
        iter_max_iter=1000,
        iter_tol=0.05,
        switch_threshold=0.1,
        newton_max_iter=20,
        newton_tol=1e-4,
        verbose=True
    )

    U_sol, info = solver.solve(system, U_init, t=0.0)

    # 
    h_sol, Q_sol = system.unpack_state(U_sol)

    print("=" * 100)
    print("")
    print("=" * 100)
    print(f"  : {'' if info['converged'] else ''}")
    print(f"  : {info['total_iterations']}")
    print(f"  : {info['total_time']:.4f}s")
    print(f"  : {h_sol.min():.4f} - {h_sol.max():.4f} m")
    print(f"  : {Q_sol.min():.4f} - {Q_sol.max():.4f} m³/s")
    print()


if __name__ == '__main__':
    main()
