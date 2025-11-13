#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov - WENO-33


1.  FVM- 
2.  WENO-3 - 3+
3.  HLL Riemann
4.  TVD-RK2 

Phase 2 - 

:
- Jiang & Shu (1996) "Efficient implementation of weighted ENO schemes"
- Toro (2009) "Riemann Solvers and Numerical Methods"

: HydroClaude Team
: 2025-10-27
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.godunov_fvm_solver import GodunvFVMSolver


class GodunvFVMWENO3(GodunvFVMSolver):
    """
    Godunov-FVM + WENO-3
    
    Phase 1GodunvFVMSolverMUSCLWENO-3
    
    WENO-3
    - 3
    - 2stencils
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
        cfl: float = 0.5,
        eps_dry: float = 1e-6,
        weno_epsilon: float = 1e-5,
        riemann_solver: str = 'hll',
        well_balanced: bool = False,
        use_numba: bool = True,
        dt_max: Optional[float] = None,
        entropy_fix: bool = False,
        critical_flow_treatment: bool = False,
        use_enhanced_bc: bool = True
    ):
        """
        

        Args:
            ()
            weno_epsilon: WENO
            riemann_solver: Riemann ('hll'  'hllc')
            well_balanced: Well-Balanced
            use_numba: Numba
            dt_max: 
            entropy_fix: Harten-Hyman entropy
            critical_flow_treatment: 
            use_enhanced_bc: 3
        """
        # order=3
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            order=3,  # 3
            riemann_solver=riemann_solver,
            well_balanced=well_balanced,
            use_numba=use_numba,
            dt_max=dt_max,
            entropy_fix=entropy_fix,
            critical_flow_treatment=critical_flow_treatment
        )

        self.weno_eps = weno_epsilon
        self.use_enhanced_bc = use_enhanced_bc

        print(f"  WENO-3")
        print(f"  : 3")
        print(f"  epsilon: {self.weno_eps}")
        if use_enhanced_bc:
            print(f"  : 3Ghost Cell")

    def _extend_with_ghosts(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        with ghost cellsWENO3

        32ghost cells per side
        

        Args:
            h:  [n]
            Q:  [n]

        Returns:
            h_ext:  [n+4] (2ghost + n + 2ghost)
            Q_ext:  [n+4]

        
            ghost_left_2 = 0
            ghost_left_1 = 1
            physical[0] = 2
            physical[1] = 3
            ...
            physical[n-1] = n+1
            ghost_right_1 = n+2
            ghost_right_2 = n+3
        """
        if not self.use_enhanced_bc:
            # 1ghost cell
            return super()._extend_with_ghosts(h, Q)

        n = len(h)
        h_ext = np.zeros(n + 4)
        Q_ext = np.zeros(n + 4)

        #  (2 to n+1)
        h_ext[2:n+2] = h
        Q_ext[2:n+2] = Q

        # =====  ghost cells (0, 1) =====
        bc_type = self.bc_left['type']

        if bc_type in ['h', 'fixed_h']:
            # 
            value = self.bc_left.get('value', self.bc_left.get('h', h[0]))
            h_bc = value if not callable(value) else value(self.t)

            # Ghost cells
            h_ext[1] = h_bc
            h_ext[0] = h_bc

            # 
            Q_ext[1] = 2*Q[0] - Q[1]
            Q_ext[0] = 2*Q_ext[1] - Q[0]

        elif bc_type in ['Q', 'fixed_Q']:
            # 
            value = self.bc_left.get('value', self.bc_left.get('Q', Q[0]))
            Q_bc = value if not callable(value) else value(self.t)

            # Ghost cells
            Q_ext[1] = Q_bc
            Q_ext[0] = Q_bc

            # 
            h_ext[1] = 2*h[0] - h[1]
            h_ext[0] = 2*h_ext[1] - h[0]

        elif bc_type == 'transmissive':
            # 
            h_ext[1] = h[0]
            h_ext[0] = h[0]
            Q_ext[1] = Q[0]
            Q_ext[0] = Q[0]

        elif bc_type == 'reflective':
            # 
            h_ext[1] = h[0]
            h_ext[0] = h[1]
            Q_ext[1] = -Q[0]  # 
            Q_ext[0] = -Q[1]

        else:
            # 
            h_ext[1] = 2*h[0] - h[1]
            h_ext[0] = 2*h_ext[1] - h[0]
            Q_ext[1] = 2*Q[0] - Q[1]
            Q_ext[0] = 2*Q_ext[1] - Q[0]

        # =====  ghost cells (n+2, n+3) =====
        bc_type = self.bc_right['type']

        if bc_type in ['h', 'fixed_h']:
            # 
            value = self.bc_right.get('value', self.bc_right.get('h', h[-1]))
            h_bc = value if not callable(value) else value(self.t)

            h_ext[n+2] = h_bc
            h_ext[n+3] = h_bc

            # 
            Q_ext[n+2] = 2*Q[-1] - Q[-2]
            Q_ext[n+3] = 2*Q_ext[n+2] - Q[-1]

        elif bc_type in ['Q', 'fixed_Q']:
            # 
            value = self.bc_right.get('value', self.bc_right.get('Q', Q[-1]))
            Q_bc = value if not callable(value) else value(self.t)

            Q_ext[n+2] = Q_bc
            Q_ext[n+3] = Q_bc

            # 
            h_ext[n+2] = 2*h[-1] - h[-2]
            h_ext[n+3] = 2*h_ext[n+2] - h[-1]

        elif bc_type == 'transmissive':
            # 
            h_ext[n+2] = h[-1]
            h_ext[n+3] = h[-1]
            Q_ext[n+2] = Q[-1]
            Q_ext[n+3] = Q[-1]

        elif bc_type == 'reflective':
            # 
            h_ext[n+2] = h[-1]
            h_ext[n+3] = h[-2]
            Q_ext[n+2] = -Q[-1]  # 
            Q_ext[n+3] = -Q[-2]

        else:
            # 
            h_ext[n+2] = 2*h[-1] - h[-2]
            h_ext[n+3] = 2*h_ext[n+2] - h[-1]
            Q_ext[n+2] = 2*Q[-1] - Q[-2]
            Q_ext[n+3] = 2*Q_ext[n+2] - Q[-1]

        # ghost cells
        h_ext = np.maximum(h_ext, self.eps_dry)

        return h_ext, Q_ext

    def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        +
        
        WENO-3MUSCL
        
        dU/dt = L(U) = -1/dx*(F_{i+1/2} - F_{i-1/2}) + S
        """
        n = len(h)
        
        # 
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        # ghost cells
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # ===== WENO-3=====
        h_L, h_R = self._weno3_reconstruction(h_ext)
        Q_L, Q_R = self._weno3_reconstruction(Q_ext)
        
        # HLL Riemann
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)
        
        for i in range(n + 1):
            F_h[i], F_Q[i] = self._hll_flux(
                h_L[i], Q_L[i], h_R[i], Q_R[i]
            )
        
        # 
        for i in range(n):
            # i
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx

            # cell_idxwell-balanced
            dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)
        
        return dh_dt, dQ_dt
    
    def _weno3_reconstruction(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-33+

        phi_i

        Args:
            phi: 
                - use_enhanced_bc=True: [n+4] (2ghost cells per side)
                - use_enhanced_bc=False: [n+2] (1ghost cell per side)

        Returns:
            phi_L:  [n+1] ()
            phi_R:  [n+1] ()

        WENO-3
        ----------------
        
            Stencil 1 (): phi_{i-1}, phi_i
            Stencil 2 (): phi_i, phi_{i+1}

        
            phi^(1) = 3/2*phi_i - 1/2*phi_{i-1}
            phi^(2) = 1/2*phi_i + 1/2*phi_{i+1}

        
            beta_1 = (phi_i - phi_{i-1})^2
            beta_2 = (phi_{i+1} - phi_i)^2

        
            d_1 = 1/3, d_2 = 2/3

        
            alpha_k = d_k / (epsilon + beta_k)^2
            omega_k = alpha_k / sum(alpha_k)

        WENO
            phi_{i+1/2}^- = omega_1*phi^(1) + omega_2*phi^(2)
        """
        if self.use_enhanced_bc:
            # n+4
            return self._weno3_reconstruction_enhanced(phi)
        else:
            # n+2
            return self._weno3_reconstruction_standard(phi)

    def _weno3_reconstruction_enhanced(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3 - 

        2ghost cells53

        Args:
            phi:  [n+4]

        Returns:
            phi_L, phi_R:  [n+1]

        Python
        """
        # 
        n = len(phi) - 4

        eps = self.weno_eps

        # 
        d1 = 1.0 / 3.0
        d2 = 2.0 / 3.0

        # ===== =====
        # n+1
        i = np.arange(n + 1)
        idx_L = i + 1  # 
        idx_R = i + 2  # 

        # -----  phi_{i+1/2}^- -----
        # 1: phi[idx_L-1], phi[idx_L]
        phi1_L = 1.5 * phi[idx_L] - 0.5 * phi[idx_L-1]

        # 2: phi[idx_L], phi[idx_L+1]
        phi2_L = 0.5 * phi[idx_L] + 0.5 * phi[idx_L+1]

        # 
        beta1_L = (phi[idx_L] - phi[idx_L-1])**2
        beta2_L = (phi[idx_L+1] - phi[idx_L])**2

        # 
        alpha1_L = d1 / (eps + beta1_L)**2
        alpha2_L = d2 / (eps + beta2_L)**2

        sum_alpha_L = alpha1_L + alpha2_L
        omega1_L = alpha1_L / sum_alpha_L
        omega2_L = alpha2_L / sum_alpha_L

        # WENO
        phi_L = omega1_L * phi1_L + omega2_L * phi2_L

        # -----  phi_{i+1/2}^+ -----
        # 1: phi[idx_R], phi[idx_R+1]
        phi1_R = 1.5 * phi[idx_R] - 0.5 * phi[idx_R+1]

        # 2: phi[idx_R-1], phi[idx_R]
        phi2_R = 0.5 * phi[idx_R] + 0.5 * phi[idx_R-1]

        # 
        beta1_R = (phi[idx_R] - phi[idx_R+1])**2
        beta2_R = (phi[idx_R-1] - phi[idx_R])**2

        # 
        alpha1_R = d1 / (eps + beta1_R)**2
        alpha2_R = d2 / (eps + beta2_R)**2

        sum_alpha_R = alpha1_R + alpha2_R
        omega1_R = alpha1_R / sum_alpha_R
        omega2_R = alpha2_R / sum_alpha_R

        # WENO
        phi_R = omega1_R * phi1_R + omega2_R * phi2_R

        return phi_L, phi_R

    def _weno3_reconstruction_enhanced_loop(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3 - 

        
        """
        # 
        n = len(phi) - 4

        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)

        eps = self.weno_eps

        # 
        d1 = 1.0 / 3.0
        d2 = 2.0 / 3.0

        # ===== =====
        for i in range(n + 1):
            # ii-1i
            # 02
            # iidx = i + 2
            # i:
            #   - : phi[idx-1], phi[idx], phi[idx+1]
            #   - : phi[idx], phi[idx+1], phi[idx+2]
            # idx+2 = (n) + 2 + 2 = n+4phi[0...n+3]
            # i=nidx=n+2, idx+2=n+4

            # iidx=i+1i+2
            # 
            #   - : [g0, g1, p0, p1, ..., p(n-1), g_n, g_n+1]
            #   - :     [0,  1,  2,  3,  ..., n+1,    n+2,  n+3]
            #   - 012
            #   - ii+1i+2
            #   - nn+1n+2

            # i+1/2
            # ii+2
            # i+1i+3

            # Let me reconsider the indexing:
            # Physical cells: [0, 1, ..., n-1]
            # Extended array: [ghost-1, ghost0, cell0, cell1, ..., cell(n-1), ghostn, ghostn+1]
            # Extended index: [0,       1,      2,     3,     ..., n+1,        n+2,   n+3]
            # Interface i is between cell(i-1) and cell(i)
            # For interface i=0: between ghost0 and cell0 (extended indices 1 and 2)
            # For interface i=n: between cell(n-1) and ghostn (extended indices n+1 and n+2)

            # For left reconstruction at interface i (from left cell i-1 in physical, or i+1 in extended):
            # We need stencil around cell i-1: [i-2, i-1, i, i+1] in physical = [i, i+1, i+2, i+3] in extended
            # But for i=0, physical i-1 doesn't exist, we use ghosts

            # Actually, let's keep it simple:
            # For interface i, in extended array:
            #   Left value uses cells around index i+1: need i, i+1, i+2
            #   Right value uses cells around index i+2: need i+1, i+2, i+3
            # Max index needed: i+3, for i=n, that's n+3, which is valid!

            # Correction: the issue is idx = i+2 is wrong, should be based on interface position

            # Let's use simpler indexing:
            # Interface i in physical is between cells i-1 and i
            # In extended array (offset by 2), it's between extended[i+1] and extended[i+2]

            # For left reconstruction (from cell i-1, extended i+1):
            #   Need stencil: extended[i], extended[i+1], extended[i+2]
            # For right reconstruction (from cell i, extended i+2):
            #   Need stencil: extended[i+1], extended[i+2], extended[i+3]

            # Max index: i+3, when i=n, that's n+3 [OK] (valid for array of size n+4)

            # -----  phi_{i+1/2}^- (from cell i-1, extended index i+1) -----
            # Stencil: [i, i+1, i+2]
            idx_L = i + 1

            # 1: phi[i], phi[i+1]
            phi1_L = 1.5 * phi[idx_L] - 0.5 * phi[idx_L-1] if idx_L > 0 else phi[idx_L]

            # 2: phi[i+1], phi[i+2]
            phi2_L = 0.5 * phi[idx_L] + 0.5 * phi[idx_L+1]

            # 
            beta1_L = (phi[idx_L] - phi[idx_L-1])**2 if idx_L > 0 else 0.0
            beta2_L = (phi[idx_L+1] - phi[idx_L])**2

            # 
            alpha1_L = d1 / (eps + beta1_L)**2
            alpha2_L = d2 / (eps + beta2_L)**2

            sum_alpha_L = alpha1_L + alpha2_L
            omega1_L = alpha1_L / sum_alpha_L
            omega2_L = alpha2_L / sum_alpha_L

            # WENO
            phi_L[i] = omega1_L * phi1_L + omega2_L * phi2_L

            # -----  phi_{i+1/2}^+ (from cell i, extended index i+2) -----
            # Stencil: [i+1, i+2, i+3]
            idx_R = i + 2

            # 1: phi[i+2], phi[i+3]
            phi1_R = 1.5 * phi[idx_R] - 0.5 * phi[idx_R+1] if idx_R+1 < len(phi) else phi[idx_R]

            # 2: phi[i+1], phi[i+2]
            phi2_R = 0.5 * phi[idx_R] + 0.5 * phi[idx_R-1]

            # 
            beta1_R = (phi[idx_R] - phi[idx_R+1])**2 if idx_R+1 < len(phi) else 0.0
            beta2_R = (phi[idx_R-1] - phi[idx_R])**2

            # 
            alpha1_R = d1 / (eps + beta1_R)**2
            alpha2_R = d2 / (eps + beta2_R)**2

            sum_alpha_R = alpha1_R + alpha2_R
            omega1_R = alpha1_R / sum_alpha_R
            omega2_R = alpha2_R / sum_alpha_R

            # WENO
            phi_R[i] = omega1_R * phi1_R + omega2_R * phi2_R

        return phi_L, phi_R

    def _weno3_reconstruction_standard(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3 - 

        1ghost cell1

        Args:
            phi:  [n+2]

        Returns:
            phi_L, phi_R:  [n+1]
        """
        n = len(phi) - 2  # 

        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)

        eps = self.weno_eps

        # 
        d1 = 1.0 / 3.0
        d2 = 2.0 / 3.0

        # =====  =====
        for i in range(n + 1):
            # -----  phi_{i+1/2}^- -----
            # 1: phi_{i-1}, phi_i
            if i > 0:
                phi1_L = 1.5 * phi[i] - 0.5 * phi[i-1]
                beta1_L = (phi[i] - phi[i-1])**2
            else:
                # 1
                phi1_L = phi[i]
                beta1_L = 0.0

            # 2: phi_i, phi_{i+1}
            if i < n:
                phi2_L = 0.5 * phi[i] + 0.5 * phi[i+1]
                beta2_L = (phi[i+1] - phi[i])**2
            else:
                # 1
                phi2_L = phi[i]
                beta2_L = 0.0

            # 
            alpha1_L = d1 / (eps + beta1_L)**2
            alpha2_L = d2 / (eps + beta2_L)**2

            sum_alpha_L = alpha1_L + alpha2_L
            if sum_alpha_L > 1e-20:
                omega1_L = alpha1_L / sum_alpha_L
                omega2_L = alpha2_L / sum_alpha_L
            else:
                omega1_L = d1
                omega2_L = d2

            # WENO
            phi_L[i] = omega1_L * phi1_L + omega2_L * phi2_L

            # -----  phi_{i+1/2}^+ -----
            # 1: phi_{i+1}, phi_{i+2}
            if i < n - 1:
                phi1_R = 1.5 * phi[i+1] - 0.5 * phi[i+2]
                beta1_R = (phi[i+1] - phi[i+2])**2
            else:
                phi1_R = phi[i+1]
                beta1_R = 0.0

            # 2: phi_i, phi_{i+1}
            if i < n:
                phi2_R = 0.5 * phi[i+1] + 0.5 * phi[i]
                beta2_R = (phi[i] - phi[i+1])**2
            else:
                phi2_R = phi[i+1]
                beta2_R = 0.0

            # 
            alpha1_R = d1 / (eps + beta1_R)**2
            alpha2_R = d2 / (eps + beta2_R)**2

            sum_alpha_R = alpha1_R + alpha2_R
            if sum_alpha_R > 1e-20:
                omega1_R = alpha1_R / sum_alpha_R
                omega2_R = alpha2_R / sum_alpha_R
            else:
                omega1_R = d1
                omega2_R = d2

            # WENO
            phi_R[i] = omega1_R * phi1_R + omega2_R * phi2_R

        return phi_L, phi_R
    
    def get_diagnostics(self) -> Dict:
        """
        
        
        Returns:
            WENO
        """
        # 
        mass_current = self._compute_total_mass()
        mass_error = (mass_current - self.initial_mass) / self.initial_mass * 100
        
        h_safe = np.maximum(self.h, self.eps_dry)
        A = h_safe * self.B
        u = self.Q / A
        c = np.sqrt(self.g * h_safe)
        Fr = np.abs(u) / c
        
        diag = {
            't': self.t,
            'step_count': self.step_count,
            'dt': self.dt,
            'h_mean': np.mean(self.h),
            'h_max': np.max(self.h),
            'h_min': np.min(self.h),
            'Q_mean': np.mean(self.Q),
            'Q_max': np.max(self.Q),
            'Q_min': np.min(self.Q),
            'Fr_mean': np.mean(Fr),
            'Fr_max': np.max(Fr),
            'mass_error': mass_error,
            'mass_current': mass_current,
            'mass_initial': self.initial_mass,
            # WENO
            'spatial_order': 3,
            'reconstruction': 'WENO-3',
            'weno_epsilon': self.weno_eps
        }
        
        return diag


# =====  =====
if __name__ == '__main__':
    print("="*70)
    print("WENO-3")
    print("="*70)
    
    # 
    solver = GodunvFVMWENO3(
        width=10.0,
        length=1000.0,
        n_cells=100,
        manning_n=0.025,
        slope=0.001,
        cfl=0.5
    )
    
    # 
    h_init = np.ones(100) * 2.0
    Q_init = np.ones(100) * 20.0
    
    bc_left = {'type': 'fixed_Q', 'Q': 20.0}
    bc_right = {'type': 'fixed_h', 'h': 2.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 10
    print("\n10:")
    for step in range(10):
        solver.step()
        
        if (step + 1) % 5 == 0:
            diag = solver.get_diagnostics()
            print(f"   {step+1}: h_avg={diag['h_mean']:.3f}m, "
                  f"Q_avg={diag['Q_mean']:.2f}m³/s, "
                  f"mass_error={diag['mass_error']:.6f}%")
    
    print("\n WENO-3!")
    print(f"  : 3")
    print(f"  : WENO-3")
    print(f"  : TVD-RK2")
    
    # 
    final_diag = solver.get_diagnostics()
    print(f"\n:")
    print(f"  : {final_diag['mass_error']:.6f}%")
    print(f"  : {final_diag['h_mean']:.3f} m")
    print(f"  : {final_diag['Q_mean']:.2f} m³/s")
