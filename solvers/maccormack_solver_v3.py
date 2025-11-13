#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacCormack v3.0 - TVD


1.  FVM
2.  RiemannHLLC- 
3.  TVD - 
4.  

: HydroClaude Team
: 2025-10-29
"""

import numpy as np
from typing import Tuple, Dict, Optional


class MacCormackSolverV3:
    """
    MacCormack v3.0
    
    
    1. HLL Riemann
    2. TVD
    3. Ghost cell
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
        use_tvd: bool = True
    ):
        """"""
        self.B = width
        self.L = length
        self.n_cells = n_cells
        self.dx = length / n_cells
        self.n = manning_n
        self.S0 = slope
        self.g = g
        self.cfl = cfl
        self.eps_dry = eps_dry
        self.use_tvd = use_tvd
        
        # 
        self.h = np.zeros(n_cells)
        self.Q = np.zeros(n_cells)
        self.x = np.linspace(0.5*self.dx, length - 0.5*self.dx, n_cells)
        
        self.t = 0.0
        self.dt = 0.0
        self.bc_left = None
        self.bc_right = None
        self.initial_mass = 0.0
        
        print(f"MacCormack v3.0 (HLLC+TVD):")
        print(f"  : {n_cells}, dx={self.dx:.3f}m")
        print(f"  TVD: {'' if use_tvd else ''}")
    
    def initialize(self, h_init, Q_init, bc_left, bc_right):
        """"""
        self.h = h_init.copy()
        self.Q = Q_init.copy()
        self.bc_left = bc_left
        self.bc_right = bc_right
        self.initial_mass = np.sum(self.h * self.B * self.dx)
        print(f"  : {self.initial_mass:.2f} m³")
    
    def compute_dt(self) -> float:
        """CFL"""
        h_safe = np.maximum(self.h, self.eps_dry)
        u = self.Q / (h_safe * self.B)
        c = np.sqrt(self.g * h_safe)
        lambda_max = np.max(np.abs(u) + c)
        return self.cfl * self.dx / lambda_max if lambda_max > 1e-10 else 1.0
    
    def step(self, dt: Optional[float] = None):
        """"""
        if dt is None:
            dt = self.compute_dt()
        self.dt = dt
        
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        # 
        h_pred, Q_pred = self._euler_step_forward(h_n, Q_n, dt)
        
        # 
        h_corr, Q_corr = self._euler_step_backward(h_pred, Q_pred, dt)
        
        # 
        h_avg = 0.5 * (h_n + h_corr)
        Q_avg = 0.5 * (Q_n + Q_corr)
        
        # TVD
        if self.use_tvd:
            self.h, self.Q = self._apply_tvd_correction(h_n, Q_n, h_avg, Q_avg)
        else:
            self.h, self.Q = h_avg, Q_avg
        
        # 
        self._enforce_boundary_conditions()
        
        # 
        self.h = np.maximum(self.h, 0.0)
        
        self.t += dt
        return self.h.copy(), self.Q.copy()
    
    def _euler_step_forward(self, h, Q, dt):
        """Riemann"""
        n = len(h)
        h_new = h.copy()
        Q_new = Q.copy()
        
        # 
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # 
        for i in range(1, n+1):
            idx = i - 1
            
            # ii+1
            F_h_right, F_Q_right = self._hll_flux(
                h_ext[i], Q_ext[i], h_ext[i+1], Q_ext[i+1]
            )
            
            # i-1i
            F_h_left, F_Q_left = self._hll_flux(
                h_ext[i-1], Q_ext[i-1], h_ext[i], Q_ext[i]
            )
            
            # 
            S_Q = self._compute_source_term(h[idx], Q[idx])
            
            # 
            h_new[idx] = h[idx] - dt/self.dx * (F_h_right - F_h_left)
            Q_new[idx] = Q[idx] - dt/self.dx * (F_Q_right - F_Q_left) + dt * S_Q
        
        return h_new, Q_new
    
    def _euler_step_backward(self, h, Q, dt):
        """"""
        n = len(h)
        h_new = h.copy()
        Q_new = Q.copy()
        
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        for i in range(1, n+1):
            idx = i - 1
            
            # ii+1
            F_h_right, F_Q_right = self._hll_flux(
                h_ext[i], Q_ext[i], h_ext[i+1], Q_ext[i+1]
            )
            
            F_h_left, F_Q_left = self._hll_flux(
                h_ext[i-1], Q_ext[i-1], h_ext[i], Q_ext[i]
            )
            
            S_Q = self._compute_source_term(h[idx], Q[idx])
            
            h_new[idx] = h[idx] - dt/self.dx * (F_h_right - F_h_left)
            Q_new[idx] = Q[idx] - dt/self.dx * (F_Q_right - F_Q_left) + dt * S_Q
        
        return h_new, Q_new
    
    def _hll_flux(self, h_L, Q_L, h_R, Q_R):
        """
        HLL Riemann
        
        
        """
        # 
        A_L = max(h_L * self.B, self.eps_dry * self.B)
        A_R = max(h_R * self.B, self.eps_dry * self.B)
        
        u_L = Q_L / A_L
        u_R = Q_R / A_R
        
        c_L = np.sqrt(self.g * h_L) if h_L > self.eps_dry else 0.0
        c_R = np.sqrt(self.g * h_R) if h_R > self.eps_dry else 0.0
        
        # 
        S_L = min(u_L - c_L, u_R - c_R)
        S_R = max(u_L + c_L, u_R + c_R)
        
        # 
        F_h_L = Q_L
        F_Q_L = Q_L**2 / A_L + 0.5 * self.g * h_L**2 * self.B
        
        F_h_R = Q_R
        F_Q_R = Q_R**2 / A_R + 0.5 * self.g * h_R**2 * self.B
        
        # HLL
        if S_L >= 0:
            return F_h_L, F_Q_L
        elif S_R <= 0:
            return F_h_R, F_Q_R
        else:
            # 
            U_h_L = h_L
            U_h_R = h_R
            U_Q_L = Q_L
            U_Q_R = Q_R
            
            F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
            F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)
            
            return F_h, F_Q
    
    def _apply_tvd_correction(self, h_old, Q_old, h_new, Q_new):
        """TVDMinMod"""
        n = len(h_new)
        h_tvd = h_new.copy()
        Q_tvd = Q_new.copy()
        
        for i in range(1, n-1):
            # h
            dh_forward = h_new[i+1] - h_new[i]
            dh_backward = h_new[i] - h_new[i-1]
            dh_limited = self._minmod(dh_forward, dh_backward)
            
            # Q
            dQ_forward = Q_new[i+1] - Q_new[i]
            dQ_backward = Q_new[i] - Q_new[i-1]
            dQ_limited = self._minmod(dQ_forward, dQ_backward)
            
            # 
            h_tvd[i] = h_old[i] + dh_limited
            Q_tvd[i] = Q_old[i] + dQ_limited
        
        return h_tvd, Q_tvd
    
    def _minmod(self, a, b):
        """MinMod"""
        if a * b <= 0:
            return 0.0
        elif abs(a) < abs(b):
            return a
        else:
            return b
    
    def _extend_with_ghosts(self, h, Q):
        """Ghost cells"""
        n = len(h)
        h_ext = np.zeros(n + 2)
        Q_ext = np.zeros(n + 2)
        
        h_ext[1:n+1] = h
        Q_ext[1:n+1] = Q
        
        # ghost
        if self.bc_left['type'] == 'h':
            h_ext[0] = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            Q_ext[0] = Q[0]
        elif self.bc_left['type'] == 'Q':
            h_ext[0] = h[0]
            Q_ext[0] = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
        
        # ghost
        if self.bc_right['type'] == 'h':
            h_ext[n+1] = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            Q_ext[n+1] = Q[n-1]
        elif self.bc_right['type'] == 'Q':
            h_ext[n+1] = h[n-1]
            Q_ext[n+1] = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
        
        return h_ext, Q_ext
    
    def _compute_source_term(self, h, Q):
        """+"""
        A = max(h * self.B, self.eps_dry * self.B)
        P = self.B + 2.0 * h
        R = A / P if P > 1e-10 else 0.0
        
        if R > 1e-10 and abs(Q) > 1e-6:
            Sf = self.n**2 * Q**2 / (A**2 * R**(4.0/3.0))
            Sf = np.sign(Q) * Sf
        else:
            Sf = 0.0
        
        return self.g * A * (self.S0 - Sf)
    
    def _enforce_boundary_conditions(self):
        """"""
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            self.h[0] = value if not callable(value) else value(self.t)
        elif self.bc_left['type'] == 'Q':
            value = self.bc_left['value']
            self.Q[0] = value if not callable(value) else value(self.t)
        
        if self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            self.h[-1] = value if not callable(value) else value(self.t)
        elif self.bc_right['type'] == 'Q':
            value = self.bc_right['value']
            self.Q[-1] = value if not callable(value) else value(self.t)
    
    def get_mass_conservation_error(self):
        """"""
        current_mass = np.sum(self.h * self.B * self.dx)
        if self.initial_mass > 1e-10:
            return (current_mass - self.initial_mass) / self.initial_mass * 100.0
        return 0.0
    
    def get_state(self):
        """"""
        return {
            'x': self.x.copy(),
            'h': self.h.copy(),
            'Q': self.Q.copy(),
            't': self.t,
            'dt': self.dt,
            'mass_error': self.get_mass_conservation_error()
        }


if __name__ == "__main__":
    print("="*80)
    print("MacCormack v3.0 (HLL+TVD) - ")
    print("="*80)
    
    # 
    print("\n1: ")
    solver = MacCormackSolverV3(
        width=10.0, length=1000.0, n_cells=50,
        manning_n=0.025, slope=0.001, cfl=0.5
    )
    
    h_init = np.ones(50) * 2.0
    Q_init = np.zeros(50)
    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 2.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    for _ in range(100):
        solver.step()
    
    state = solver.get_state()
    print(f"  : {state['mass_error']:.6f}%")
    print(f"  : {'' if abs(state['mass_error']) < 0.5 else ''}")
