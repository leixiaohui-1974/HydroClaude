#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov - WENO-55


1.  FVM- 
2.  WENO-5 - 5+
3.  HLL Riemann
4.  TVD-RK3 3

MacDonald Test 4

:
- Jiang & Shu (1996) "Efficient implementation of weighted ENO schemes"
- Toro (2009) "Riemann Solvers and Numerical Methods"

: HydroClaude Team
: 2025-10-31
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.godunov_fvm_solver import GodunvFVMSolver
from solvers.weno5_reconstruction import weno5_reconstruct


class GodunvFVMWENO5(GodunvFVMSolver):
    """
    Godunov-FVM + WENO-5

    GodunvFVMSolverWENO-5MUSCL

    WENO-5
    - 5
    - 3stencils
    - 
    - 
    - 
    """

    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.4,  # WENO5CFL
        eps_dry: float = 1e-6,
        weno_epsilon: float = 1e-6,
        riemann_solver: str = 'hll',
        well_balanced: bool = False,
        use_numba: bool = True,
        dt_max: Optional[float] = None,
        entropy_fix: bool = False,
        critical_flow_treatment: bool = False
    ):
        """
        WENO5

        Args:
            ()
            weno_epsilon: WENO
            riemann_solver: Riemann ('hll')
            well_balanced: Well-Balanced
            use_numba: Numba
            dt_max: 
            entropy_fix: Harten-Hyman entropy
            critical_flow_treatment: 
        """
        # 5
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            order=5,  # 5
            riemann_solver=riemann_solver,
            well_balanced=well_balanced,
            use_numba=use_numba,
            dt_max=dt_max,
            entropy_fix=entropy_fix,
            critical_flow_treatment=critical_flow_treatment
        )

        self.weno_eps = weno_epsilon

        print(f"  WENO-5")
        print(f"  : 5")
        print(f"  epsilon: {self.weno_eps}")

    def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        +

        WENO-5MUSCL

        dU/dt = L(U) = -1/dx*(F_{i+1/2} - F_{i-1/2}) + S
        """
        n = len(h)

        # 
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)

        # WENO52ghost cells
        h_ext, Q_ext = self._extend_with_ghosts_weno5(h, Q)

        # ===== WENO-5=====
        # weno5_reconstruct
        # : n+4ghost
        # : n+1

        h_L_ext, h_R_ext = weno5_reconstruct(h_ext, self.weno_eps)
        Q_L_ext, Q_R_ext = weno5_reconstruct(Q_ext, self.weno_eps)

        # weno5_reconstruct(n+4)-1 = n+3
        # 2n+2n+1

        # HLL Riemann
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        for i in range(n + 1):
            # ii+2
            idx = i + 2
            if idx < len(h_L_ext):
                F_h[i], F_Q[i] = self._hll_flux(
                    h_L_ext[idx], Q_L_ext[idx], h_R_ext[idx], Q_R_ext[idx]
                )
            else:
                # 
                idx = len(h_L_ext) - 1
                F_h[i], F_Q[i] = self._hll_flux(
                    h_L_ext[idx], Q_L_ext[idx], h_R_ext[idx], Q_R_ext[idx]
                )

        # 
        for i in range(n):
            # i
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx

            # 
            dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

        return dh_dt, dQ_dt

    def _extend_with_ghosts_weno5(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        2ghost cellsWENO5

        Args:
            h, Q:  [n]

        Returns:
            h_ext, Q_ext:  [n+4] (2ghost + n + 2ghost)
        """
        n = len(h)

        h_ext = np.zeros(n + 4)
        Q_ext = np.zeros(n + 4)

        # 
        h_ext[2:-2] = h
        Q_ext[2:-2] = Q

        # ghost cells
        if self.bc_left['type'] == 'supercritical':
            # 
            h_ext[0] = self.bc_left['h']
            h_ext[1] = self.bc_left['h']
            Q_ext[0] = self.bc_left['Q']
            Q_ext[1] = self.bc_left['Q']
        else:
            # 0
            h_ext[0] = h[0]
            h_ext[1] = h[0]
            Q_ext[0] = Q[0]
            Q_ext[1] = Q[0]

        # ghost cells
        if self.bc_right['type'] == 'fixed_h':
            # 
            h_ext[-2] = self.bc_right['h']
            h_ext[-1] = self.bc_right['h']
            Q_ext[-2] = Q[-1]  # 
            Q_ext[-1] = Q[-1]
        else:
            # 0
            h_ext[-2] = h[-1]
            h_ext[-1] = h[-1]
            Q_ext[-2] = Q[-1]
            Q_ext[-1] = Q[-1]

        return h_ext, Q_ext


def test_weno5_solver():
    """WENO5"""
    print("="*80)
    print("WENO5")
    print("="*80)

    # 
    L = 100.0
    B = 10.0
    n_cells = 50

    solver = GodunvFVMWENO5(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        g=9.81,
        cfl=0.4,
        eps_dry=1e-6,
        weno_epsilon=1e-6
    )

    # 
    h_init = np.ones(n_cells)
    h_init[:n_cells//2] = 0.5
    h_init[n_cells//2:] = 1.0

    Q_init = np.ones(n_cells) * 5.0

    bc_left = {'type': 'supercritical', 'h': 0.5, 'Q': 5.0}
    bc_right = {'type': 'fixed_h', 'h': 1.0}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n10...")
    for _ in range(10):
        solver.step()

    print(f"\n:")
    print(f"  : t={solver.t:.3f}s")
    print(f"  : {solver.step_count}")
    print(f"  : [{solver.h.min():.3f}, {solver.h.max():.3f}]")
    print(f"  : [{solver.Q.min():.3f}, {solver.Q.max():.3f}]")

    # 
    if np.all(np.isfinite(solver.h)) and np.all(np.isfinite(solver.Q)):
        print("\n WENO5")
        return True
    else:
        print("\n NaN/Inf")
        return False


if __name__ == '__main__':
    success = test_weno5_solver()
    exit(0 if success else 1)
