#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


 A·x = b 
V-cycle

: Claude
: 2025-10-22
"""

import numpy as np
from scipy.sparse import csr_matrix, diags, lil_matrix
from scipy.sparse.linalg import spsolve
from typing import List, Optional, Tuple


class MultiGridSolver:
    """
    

    
    - V-cycle
    - 
    - 
    - Gauss-Seidel
    - 
    """

    def __init__(self,
                 n_levels: Optional[int] = None,
                 nu1: int = 2,
                 nu2: int = 2,
                 coarsest_size: int = 20,
                 verbose: bool = False):
        """
        Args:
            n_levels: None
            nu1: 
            nu2: 
            coarsest_size: 
            verbose: 
        """
        self.n_levels = n_levels
        self.nu1 = nu1
        self.nu2 = nu2
        self.coarsest_size = coarsest_size
        self.verbose = verbose

        # setup
        self.grids = []  # 
        self.R_operators = []  # 
        self.P_operators = []  # 
        self.A_hierarchy = []  # 

    def setup(self, A: csr_matrix, n_fine: int):
        """
        

        Args:
            A: 
            n_fine: 
        """
        # 
        if self.n_levels is None:
            self.n_levels = self._determine_levels(n_fine)

        if self.verbose:
            print(f"[MultiGrid]  {self.n_levels} ")

        # 
        self.grids = [n_fine]
        n_current = n_fine
        for level in range(1, self.n_levels):
            n_coarse = (n_current + 1) // 2  # 
            if n_coarse < self.coarsest_size:
                # 
                self.n_levels = level
                if self.verbose:
                    print(f"[MultiGrid]  {self.n_levels}  {n_current} ")
                break
            self.grids.append(n_coarse)
            n_current = n_coarse

        # 
        self.R_operators = []
        self.P_operators = []
        for level in range(self.n_levels - 1):
            n_f = self.grids[level]
            n_c = self.grids[level + 1]
            R = self._build_restriction(n_f, n_c)
            P = self._build_prolongation(n_f, n_c)
            self.R_operators.append(R)
            self.P_operators.append(P)

        # GalerkinA_c = R·A_f·P
        self.A_hierarchy = [A]
        for level in range(self.n_levels - 1):
            A_fine = self.A_hierarchy[level]
            R = self.R_operators[level]
            P = self.P_operators[level]
            A_coarse = R @ A_fine @ P
            self.A_hierarchy.append(A_coarse.tocsr())

        if self.verbose:
            print(f"[MultiGrid] : {self.grids}")

    def _determine_levels(self, n_fine: int) -> int:
        """"""
        levels = 1
        n = n_fine
        while n > self.coarsest_size:
            n = (n + 1) // 2
            levels += 1
            if levels > 10:  # 10
                break
        return levels

    def _build_restriction(self, n_fine: int, n_coarse: int) -> csr_matrix:
        """
        

        1D
        r_c[i] = 0.25·r_f[2i-1] + 0.5·r_f[2i] + 0.25·r_f[2i+1]

        Args:
            n_fine: 
            n_coarse: 

        Returns:
            R:  (n_coarse × n_fine)
        """
        R = lil_matrix((n_coarse, n_fine))

        for i in range(n_coarse):
            j_center = 2 * i

            if j_center >= n_fine:
                # 
                R[i, -1] = 1.0
            elif j_center == 0:
                # 
                R[i, 0] = 1.0
            elif j_center >= n_fine - 1:
                # 
                R[i, -1] = 1.0
            else:
                # 
                R[i, j_center - 1] = 0.25
                R[i, j_center] = 0.5
                R[i, j_center + 1] = 0.25

        return R.tocsr()

    def _build_prolongation(self, n_fine: int, n_coarse: int) -> csr_matrix:
        """
        

        1D
        e_f[2i] = e_c[i]
        e_f[2i+1] = 0.5·(e_c[i] + e_c[i+1])

        Args:
            n_fine: 
            n_coarse: 

        Returns:
            P:  (n_fine × n_coarse)
        """
        P = lil_matrix((n_fine, n_coarse))

        for i in range(n_coarse):
            j_center = 2 * i

            if j_center < n_fine:
                # 
                P[j_center, i] = 1.0

            # 
            j_interp = 2 * i + 1
            if j_interp < n_fine and i < n_coarse - 1:
                P[j_interp, i] = 0.5
                P[j_interp, i + 1] = 0.5
            elif j_interp < n_fine:
                # 
                P[j_interp, i] = 1.0

        return P.tocsr()

    def _smooth(self, A: csr_matrix, b: np.ndarray, x: np.ndarray,
                nu: int) -> np.ndarray:
        """
        Gauss-Seidel

        Args:
            A: 
            b: 
            x: 
            nu: 

        Returns:
            
        """
        n = len(x)
        x = x.copy()

        for _ in range(nu):
            # Red sweep
            for i in range(0, n, 2):
                row_start = A.indptr[i]
                row_end = A.indptr[i + 1]
                indices = A.indices[row_start:row_end]
                data = A.data[row_start:row_end]

                # 
                diag_idx = np.where(indices == i)[0]
                if len(diag_idx) == 0:
                    continue

                a_ii = data[diag_idx[0]]
                if abs(a_ii) < 1e-14:
                    continue

                # 
                residual = b[i] - (data @ x[indices])

                # 
                x[i] += residual / a_ii

            # Black sweep
            for i in range(1, n, 2):
                row_start = A.indptr[i]
                row_end = A.indptr[i + 1]
                indices = A.indices[row_start:row_end]
                data = A.data[row_start:row_end]

                diag_idx = np.where(indices == i)[0]
                if len(diag_idx) == 0:
                    continue

                a_ii = data[diag_idx[0]]
                if abs(a_ii) < 1e-14:
                    continue

                residual = b[i] - (data @ x[indices])
                x[i] += residual / a_ii

        return x

    def _v_cycle(self, level: int, b: np.ndarray, x: np.ndarray) -> np.ndarray:
        """
        V-cycle

        Args:
            level: 0
            b: 
            x: 

        Returns:
            
        """
        A = self.A_hierarchy[level]

        # 
        if level == self.n_levels - 1:
            try:
                x = spsolve(A, b)
            except:
                # 
                x = self._smooth(A, b, x, nu=50)
            return x

        # 
        x = self._smooth(A, b, x, self.nu1)

        # 
        r = b - A @ x

        # 
        R = self.R_operators[level]
        r_c = R @ r

        # 
        e_c = np.zeros(self.grids[level + 1])
        e_c = self._v_cycle(level + 1, r_c, e_c)

        # 
        P = self.P_operators[level]
        e = P @ e_c

        # 
        x = x + e

        # 
        x = self._smooth(A, b, x, self.nu2)

        return x

    def solve(self,
              A: csr_matrix,
              b: np.ndarray,
              x_init: Optional[np.ndarray] = None,
              n_cycles: int = 1,
              tol: float = 1e-10,
              max_cycles: int = 50) -> Tuple[np.ndarray, dict]:
        """
         A·x = b

        Args:
            A: 
            b: 
            x_init: None
            n_cycles: V-cycle
            tol: 
            max_cycles: V-cycle

        Returns:
            x: 
            info: 
        """
        n = len(b)

        # 
        self.setup(A, n)

        # 
        if x_init is None:
            x = np.zeros(n)
        else:
            x = x_init.copy()

        # 
        r0_norm = np.linalg.norm(b - A @ x)
        if r0_norm < 1e-14:
            return x, {'converged': True, 'cycles': 0, 'residual': 0.0}

        # V-cycle
        residual_history = [r0_norm]

        for cycle in range(max_cycles):
            x = self._v_cycle(0, b, x)

            # 
            r = b - A @ x
            r_norm = np.linalg.norm(r)
            residual_history.append(r_norm)

            # 
            rel_residual = r_norm / r0_norm

            if self.verbose and cycle % 5 == 0:
                print(f"  [MG] Cycle {cycle+1}: res={r_norm:.3e}, rel={rel_residual:.3e}")

            if rel_residual < tol or cycle + 1 >= n_cycles:
                converged = rel_residual < tol
                if self.verbose:
                    status = "" if converged else ""
                    print(f"  [MG] {status}: {cycle+1} cycles, rel_res={rel_residual:.3e}")

                return x, {
                    'converged': converged,
                    'cycles': cycle + 1,
                    'residual': r_norm,
                    'relative_residual': rel_residual,
                    'residual_history': residual_history
                }

        # 
        return x, {
            'converged': False,
            'cycles': max_cycles,
            'residual': r_norm,
            'relative_residual': rel_residual,
            'residual_history': residual_history
        }


def test_multigrid():
    """"""
    print("=" * 80)
    print("")
    print("=" * 80)

    # 1D Poisson -u''(x) = f(x), x∈[0,1], u(0)=u(1)=0
    # u(x) = x(1-x)/2

    n = 401  # 
    dx = 1.0 / (n - 1)

    # 
    main_diag = 2.0 / dx**2 * np.ones(n)
    off_diag = -1.0 / dx**2 * np.ones(n - 1)

    # Dirichlet
    main_diag[0] = main_diag[-1] = 1.0
    off_diag[0] = off_diag[-1] = 0.0

    A = diags([off_diag, main_diag, off_diag], [-1, 0, 1], format='csr')

    #  f(x) = 1
    b = np.ones(n)
    b[0] = b[-1] = 0.0  # 

    # 
    x_grid = np.linspace(0, 1, n)
    u_exact = x_grid * (1 - x_grid) / 2

    print(f"\n: {n} × {n}")
    print(f": {A.nnz / n**2 * 100:.2f}%")

    # 
    print("\n:")
    mg_solver = MultiGridSolver(nu1=2, nu2=2, verbose=True)

    import time
    start_time = time.time()
    u_mg, info_mg = mg_solver.solve(A, b, n_cycles=10, tol=1e-8)
    mg_time = time.time() - start_time

    error_mg = np.linalg.norm(u_mg - u_exact) / np.linalg.norm(u_exact)

    print(f"\n:")
    print(f"  V-cycles: {info_mg['cycles']}")
    print(f"  : {info_mg['converged']}")
    print(f"  : {info_mg['residual']:.3e}")
    print(f"  : {info_mg['relative_residual']:.3e}")
    print(f"  : {error_mg:.3e}")
    print(f"  : {mg_time:.4f}s")

    # 
    print("\nscipy.sparse.linalg.spsolve:")
    start_time = time.time()
    u_direct = spsolve(A, b)
    direct_time = time.time() - start_time

    error_direct = np.linalg.norm(u_direct - u_exact) / np.linalg.norm(u_exact)

    print(f"  : {error_direct:.3e}")
    print(f"  : {direct_time:.4f}s")

    print(f"\n: {direct_time / mg_time:.2f}x")
    print("=" * 80)


if __name__ == "__main__":
    test_multigrid()
