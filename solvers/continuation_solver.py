#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 + 

pseudo_dtNewton
- pseudo_dt: Jacobian
- pseudo_dt: 

: Claude
: 2025-10-22
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
    

    
    1. pseudo_dt = 10.0 → Newton
    2. pseudo_dt = 1.0  → Newton
    3. pseudo_dt = 0.1  → Newton
    """

    def __init__(self,
                 pseudo_dt_sequence: List[float] = None,
                 newton_max_iter: int = 20,
                 newton_tol: float = 1e-4,
                 verbose: bool = True):
        """
        

        Args:
            pseudo_dt_sequence: 
            newton_max_iter: Newton
            newton_tol: Newton
            verbose: 
        """
        # 10.0 → 1.0 → 0.1
        self.pseudo_dt_sequence = pseudo_dt_sequence or [10.0, 1.0, 0.1]
        self.newton_max_iter = newton_max_iter
        self.newton_tol = newton_tol
        self.verbose = verbose

    def solve(self,
              system,
              U_init: np.ndarray,
              t: float = 0.0) -> Tuple[np.ndarray, Dict]:
        """
        

        Args:
            system: SteadySaintVenantSystem
            U_init: 
            t: 

        Returns:
            U_solution: 
            info: 
        """
        start_time_total = time.time()

        if self.verbose:
            print("[ContinuationSolver] ...")
            print(f"  pseudo_dt: {self.pseudo_dt_sequence}")
            print(f"  Newton: max_iter={self.newton_max_iter}, tol={self.newton_tol}")
            print()

        # pseudo_dt
        original_pseudo_dt = system.pseudo_dt

        U_current = U_init.copy()
        all_stage_info = []

        # 
        for stage, pseudo_dt in enumerate(self.pseudo_dt_sequence):
            if self.verbose:
                print("=" * 80)
                print(f" {stage + 1}/{len(self.pseudo_dt_sequence)}: pseudo_dt = {pseudo_dt}")
                print("=" * 80)

            # pseudo_dt
            system.pseudo_dt = pseudo_dt

            # U_prev
            system.U_prev = U_current.copy()

            # Newton
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
                    print(f"  {stage + 1}: {' ' if stage_info['converged'] else ' '}")
                    print(f"  : {stage_info['iterations']}")
                    print(f"  : {time_stage:.4f}s")
                    print()

                # 
                if not stage_info['converged']:
                    if self.verbose:
                        print(f"[WARN] {stage + 1}")
                    break

            except Exception as e:
                if self.verbose:
                    print(f"   {stage + 1}: {e}")
                break

        # pseudo_dt
        system.pseudo_dt = original_pseudo_dt

        time_total = time.time() - start_time_total

        # 
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
            print("")
            print("=" * 80)
            print(f"  : {len(all_stage_info)}/{len(self.pseudo_dt_sequence)}")
            print(f"  : {total_iterations}")
            print(f"  : {time_total:.4f}s")
            print(f"  : {' ' if final_converged else ' '}")
            print()

        return U_current, info


def main():
    """"""
    from physics.steady_saint_venant import SteadySaintVenantSystem
    from solvers.gate import SluiceGate
    from utils.canal_utils import compute_steady_uniform_flow

    print("=" * 100)
    print(" - ")
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
        pseudo_dt=0.1  # 
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
    solver = ContinuationSolver(
        pseudo_dt_sequence=[10.0, 1.0, 0.1],
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

    # 
    print(":")
    for i, stage in enumerate(info['stage_info']):
        print(f"  {i+1} (pseudo_dt={stage['pseudo_dt']}): "
              f"{stage['iterations']}, {stage['time']:.4f}s")
    print()


if __name__ == '__main__':
    main()
