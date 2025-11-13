#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov - WENO-3 V2 ()


- WENO
- 
- 

: HydroClaude Team
: 2025-10-27
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.godunov_fvm_solver import GodunvFVMSolver


class GodunvFVMWENO3V2(GodunvFVMSolver):
    """
    Godunov-FVM + WENO-3 ()
    
    
    1. 
    2. 
    3. 
    """
    
    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.4,  # CFL
        eps_dry: float = 1e-6,
        weno_epsilon: float = 1e-4  # epsilon
    ):
        """"""
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            order=3
        )
        
        self.weno_eps = weno_epsilon
        
        print(f"  WENO-3V2")
        print(f"  epsilon: {self.weno_eps}")
        print(f"  CFL: {self.cfl}")
    
    def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3
        """
        n = len(h)
        
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        # Ghost cells
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # WENO-3
        h_L, h_R = self._weno3_reconstruct_simple(h_ext)
        Q_L, Q_R = self._weno3_reconstruct_simple(Q_ext)
        
        # 
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)
        
        for i in range(n + 1):
            F_h[i], F_Q[i] = self._hll_flux(
                h_L[i], Q_L[i], h_R[i], Q_R[i]
            )
        
        # +
        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx
            dQ_dt[i] += self._compute_source_term(h[i], Q[i])
        
        return dh_dt, dQ_dt
    
    def _weno3_reconstruct_simple(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3+
        
        
        1. 
        2. 
        3. 
        
        Args:
            phi: [n+2] ghost cells
        
        Returns:
            phi_L, phi_R: [n+1] 
        """
        n = len(phi) - 2
        
        eps = self.weno_eps
        d1, d2 = 1.0/3.0, 2.0/3.0
        
        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)
        
        # =====  phi_{i+1/2}^- =====
        for i in range(1, n):
            # 
            
            # 1: phi_{i-1}, phi_i
            phi1 = 1.5 * phi[i] - 0.5 * phi[i-1]
            
            # 2: phi_i, phi_{i+1}
            phi2 = 0.5 * phi[i] + 0.5 * phi[i+1]
            
            # 
            beta1 = (phi[i] - phi[i-1])**2
            beta2 = (phi[i+1] - phi[i])**2
            
            # 
            alpha1 = d1 / (eps + beta1)**2
            alpha2 = d2 / (eps + beta2)**2
            sum_alpha = alpha1 + alpha2
            
            omega1 = alpha1 / sum_alpha
            omega2 = alpha2 / sum_alpha
            
            # WENO
            phi_L[i] = omega1 * phi1 + omega2 * phi2
            
            # 
            phi_min = min(phi[i-1], phi[i], phi[i+1])
            phi_max = max(phi[i-1], phi[i], phi[i+1])
            phi_L[i] = np.clip(phi_L[i], phi_min, phi_max)
        
        # 
        phi_L[0] = phi[0]
        phi_L[n] = phi[n]
        
        # =====  phi_{i+1/2}^+ =====
        for i in range(1, n):
            # 
            
            # 1: phi_{i+1}, phi_{i+2}
            phi1 = 1.5 * phi[i+1] - 0.5 * phi[i+2]
            
            # 2: phi_i, phi_{i+1}
            phi2 = 0.5 * phi[i] + 0.5 * phi[i+1]
            
            # 
            beta1 = (phi[i+1] - phi[i+2])**2
            beta2 = (phi[i] - phi[i+1])**2
            
            # 
            alpha1 = d1 / (eps + beta1)**2
            alpha2 = d2 / (eps + beta2)**2
            sum_alpha = alpha1 + alpha2
            
            omega1 = alpha1 / sum_alpha
            omega2 = alpha2 / sum_alpha
            
            # WENO
            phi_R[i] = omega1 * phi1 + omega2 * phi2
            
            # 
            phi_min = min(phi[i], phi[i+1], phi[i+2])
            phi_max = max(phi[i], phi[i+1], phi[i+2])
            phi_R[i] = np.clip(phi_R[i], phi_min, phi_max)
        
        # 
        phi_R[0] = phi[1]
        phi_R[n] = phi[n+1]
        
        return phi_L, phi_R
    
    def get_diagnostics(self) -> Dict:
        """"""
        mass_current = self._compute_total_mass()
        mass_error = (mass_current - self.initial_mass) / self.initial_mass * 100
        
        h_safe = np.maximum(self.h, self.eps_dry)
        A = h_safe * self.B
        u = self.Q / A
        c = np.sqrt(self.g * h_safe)
        Fr = np.abs(u) / c
        
        return {
            't': self.t,
            'step_count': self.step_count,
            'dt': self.dt,
            'h_mean': np.mean(self.h),
            'Q_mean': np.mean(self.Q),
            'Fr_mean': np.mean(Fr),
            'mass_error': mass_error,
            'spatial_order': 3,
            'reconstruction': 'WENO-3 V2',
            'weno_epsilon': self.weno_eps
        }


# =====  =====
if __name__ == '__main__':
    print("="*70)
    print("WENO-3 V2")
    print("="*70)
    
    solver = GodunvFVMWENO3V2(
        width=10.0,
        length=1000.0,
        n_cells=100,
        manning_n=0.025,
        slope=0.001,
        cfl=0.4
    )
    
    # 
    h_init = np.ones(100) * 2.0
    Q_init = np.ones(100) * 20.0
    
    bc_left = {'type': 'fixed_Q', 'Q': 20.0}
    bc_right = {'type': 'fixed_h', 'h': 2.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 20
    print("\n20:")
    for step in range(20):
        solver.step()
        
        if (step + 1) % 5 == 0:
            diag = solver.get_diagnostics()
            print(f"   {step+1}: h_avg={diag['h_mean']:.3f}m, "
                  f"Q_avg={diag['Q_mean']:.2f}m³/s, "
                  f"mass_error={diag['mass_error']:.6f}%")
    
    print("\n WENO-3 V2!")
    
    # 
    final_diag = solver.get_diagnostics()
    print(f"\n:")
    print(f"  : {final_diag['mass_error']:.6f}%")
    print(f"  : {final_diag['h_mean']:.3f} m")
    print(f"  : {final_diag['Q_mean']:.2f} m³/s")
    
    # 
    if abs(final_diag['mass_error']) < 5.0 and not np.isnan(final_diag['h_mean']):
        print("\n[SUCCESS] WENO-3 V2")
    else:
        print("\n[WARN] WENO-3 V2")
