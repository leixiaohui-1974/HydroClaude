#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-

Saint-Venant

: Claude
: 2025-10-22
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
    -

    
    - 
    - O(N)
    - 
    - 
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
            length:  (m)
            nx: 
            B:  (m)
            S0: 
            n: Manning
            g:  (m/s²)
            structures:  [(position, structure), ...]
            verbose: 
        """
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.structures = structures if structures is not None else []
        self.verbose = verbose

        # Saint-Venant
        self.sv_system = SteadySaintVenantSystem(
            length, nx, B, S0, n, g, structures,
            pseudo_dt=1.0  # Jacobian
        )

        # 
        self.newton_solver = NewtonSolver(
            linear_solver='direct',  # 
            max_iter=50,
            tol_residual=1e-6,
            tol_update=1e-8,
            line_search=True,
            verbose=verbose
        )

        # 
        self.mg_solver = MultiGridSolver(
            n_levels=None,  # 
            nu1=2,
            nu2=2,
            verbose=False  # 
        )

        # solve
        self.use_multigrid = False  # 

        # 
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
        Saint-Venant

        Args:
            Q_target:  (m³/s)
            h_downstream:  (m)None
            U_init: None
            max_newton_iter: 
            tol: 
            t: 

        Returns:
            result: 
                - converged: 
                - iterations: 
                - h: 
                - Q: 
                - x: 
                - residual_norm: 
                - elapsed_time: 
                - gate_flows: 
        """
        if self.verbose:
            print("=" * 80)
            solver_name = "-" if use_multigrid else ""
            print(f"{solver_name}")
            print("=" * 80)
            print(f"  : {Q_target} m³/s")
            print(f"  : {self.nx}")
            print(f"  : {len(self.structures)}")

        # 
        if use_multigrid:
            self.newton_solver.set_multigrid_solver(self.mg_solver)
        else:
            self.newton_solver.linear_solver_type = 'direct'

        start_time = time.time()

        # 
        if h_downstream is None:
            h_downstream = compute_steady_uniform_flow(Q_target, self.B, self.S0, self.n, self.g)

        self.sv_system.set_boundary_conditions(
            Q_upstream=Q_target,
            h_downstream=h_downstream
        )

        if self.verbose:
            print(f"  : {h_downstream:.4f} m")

        # 
        if U_init is None:
            h_uniform = compute_steady_uniform_flow(Q_target, self.B, self.S0, self.n, self.g)
            h_init = np.ones(self.nx) * h_uniform
            Q_init = np.ones(self.nx) * Q_target
            U_init = self.sv_system.pack_state(h_init, Q_init)

            if self.verbose:
                print(f"  : {h_uniform:.4f} m ()")

        # Jacobian
        def residual_func(U):
            return self.sv_system.compute_residual(U, t)

        def jacobian_func(U):
            return self.sv_system.compute_jacobian(U, t)

        # 
        def callback(iter_num, U_current, F, dU, alpha):
            # 
            self.sv_system.U_prev = U_current.copy()

        # 
        if self.verbose:
            print(f"\n-...")
            print("-" * 80)

        # 
        self.sv_system.U_prev = U_init.copy()

        # 
        self.newton_solver.max_iter = max_newton_iter
        self.newton_solver.tol_residual = tol

        U_sol, info = self.newton_solver.solve(
            U_init, residual_func, jacobian_func, callback=callback
        )

        elapsed_time = time.time() - start_time

        # 
        h_sol, Q_sol = self.sv_system.unpack_state(U_sol)

        # 
        gate_flows = []
        for structure in self.sv_system.structure_objects:
            idx = self.sv_system.structure_indices[self.sv_system.structure_objects.index(structure)]
            if idx > 0 and idx < self.nx - 1:
                h_up = h_sol[idx - 1]
                h_down = h_sol[idx + 1]
                Q_gate, _ = structure.calculate_discharge(h_up, h_down, t)
                gate_flows.append(Q_gate)

        # 
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

        # 
        self.solve_history.append(result)

        if self.verbose:
            print("-" * 80)
            print(f"")
            print(f"  : {'' if result['converged'] else ''}")
            print(f"  : {result['iterations']}")
            print(f"  : {result['residual_norm']:.3e}")
            print(f"  : {result['final_error']*100:.4f}%")
            if gate_flows:
                print(f"  : {', '.join([f'{q:.3f}' for q in gate_flows])} m³/s")
            print(f"  : {elapsed_time:.4f}s")
            print("=" * 80)

        return result

    def _compute_flow_conservation_error(self, Q: np.ndarray, gate_flows: List[float]) -> float:
        """
        

        Args:
            Q: 
            gate_flows: 

        Returns:
            
        """
        Q_mean = np.mean(np.abs(Q))
        if Q_mean < 1e-6:
            return 0.0

        # 
        Q_std = np.std(Q)
        error = Q_std / Q_mean

        return error


def test_newton_multigrid():
    """-"""
    from solvers.gate import SluiceGate

    print("=" * 80)
    print("-")
    print("=" * 80)

    # 1
    print("\n1")
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

    # 2
    print("\n\n2")
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

    # 3
    print("\n\n3")
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

    # 
    print("\n\n" + "=" * 80)
    print("")
    print("=" * 80)

    scenarios = [
        ("", result1),
        ("", result2),
        ("", result3)
    ]

    print(f"{'':<15} {'':<8} {'':<10} {'':<12} {'':<12} {'(s)':<10}")
    print("-" * 80)

    for name, result in scenarios:
        converged_str = "[OK]" if result['converged'] else "[FAIL]"
        print(f"{name:<15} {converged_str:<8} {result['iterations']:<10} "
              f"{result['residual_norm']:<12.3e} {result['final_error']*100:<11.4f}% "
              f"{result['elapsed_time']:<10.4f}")

    print("=" * 80)


if __name__ == "__main__":
    test_newton_multigrid()
