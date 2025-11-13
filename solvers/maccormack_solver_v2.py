#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacCormack v2.0 - 


1.  FVM- 
2.   - 
3.   - Ghost cell
4.   - TVD

: HydroClaude Team
: 2025-10-29
"""

import numpy as np
from typing import Tuple, Dict, Optional, Callable


class MacCormackSolverV2:
    """
    MacCormack v2.0 - 
    
    
    ∂U/∂t + ∂F/∂x = S
    
    :
    U_i^{n+1} = U_i^n - dt/dx * (F_{i+1/2} - F_{i-1/2}) + dt * S_i
    
    MacCormack
    1. : U* = U^n - dt/dx*(F_{i+1/2} - F_{i-1/2})^n + dt*S^n
    2. : U** = U* - dt/dx*(F_{i+1/2} - F_{i-1/2})* + dt*S*
    3. : U^{n+1} = 0.5*(U^n + U**)
    """
    
    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.8,
        eps_dry: float = 1e-6
    ):
        """
        
        
        Args:
            width:  (m)
            length:  (m)
            n_cells: 
            manning_n: Manning
            slope: 
            g: 
            cfl: CFL
            eps_dry: 
        """
        self.B = width
        self.L = length
        self.n_cells = n_cells
        self.dx = length / n_cells
        self.n = manning_n
        self.S0 = slope
        self.g = g
        self.cfl = cfl
        self.eps_dry = eps_dry
        
        # 
        self.h = np.zeros(n_cells)
        self.Q = np.zeros(n_cells)
        
        # 
        self.x = np.linspace(0.5*self.dx, length - 0.5*self.dx, n_cells)
        
        # 
        self.t = 0.0
        self.dt = 0.0
        
        # 
        self.bc_left = None
        self.bc_right = None
        
        # 
        self.initial_mass = 0.0
        
        print(f"MacCormack v2.0 :")
        print(f"  : {n_cells}")
        print(f"  dx = {self.dx:.3f} m")
        print(f"  FVM- ")
    
    def initialize(
        self,
        h_init: np.ndarray,
        Q_init: np.ndarray,
        bc_left: Dict,
        bc_right: Dict
    ):
        """
        
        
        Args:
            h_init: [n_cells]
            Q_init: [n_cells]
            bc_left: 
            bc_right: 
        """
        self.h = h_init.copy()
        self.Q = Q_init.copy()
        self.bc_left = bc_left
        self.bc_right = bc_right
        
        # 
        self.initial_mass = np.sum(self.h * self.B * self.dx)
        
        print(f"  : {self.initial_mass:.2f} m³")
    
    def compute_dt(self) -> float:
        """CFL"""
        h_safe = np.maximum(self.h, self.eps_dry)
        u = self.Q / (h_safe * self.B)
        c = np.sqrt(self.g * h_safe)
        
        lambda_max = np.max(np.abs(u) + c)
        
        if lambda_max > 1e-10:
            dt = self.cfl * self.dx / lambda_max
        else:
            dt = 1.0
        
        return dt
    
    def step(self, dt: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        MacCormack
        """
        if dt is None:
            dt = self.compute_dt()
        
        self.dt = dt
        
        # 
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        # ===  ===
        h_pred, Q_pred = self._predictor_conservative(h_n, Q_n, dt)
        
        # ===  ===
        h_corr, Q_corr = self._corrector_conservative(h_pred, Q_pred, dt)
        
        # ===  ===
        self.h = 0.5 * (h_n + h_corr)
        self.Q = 0.5 * (Q_n + Q_corr)
        
        # ===  ===
        self._enforce_boundary_conditions()
        
        # ===  ===
        self.h = np.maximum(self.h, 0.0)
        
        self.t += dt
        
        return self.h.copy(), self.Q.copy()
    
    def _predictor_conservative(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        
        
        U_i* = U_i^n - dt/dx * (F_{i+1/2} - F_{i-1/2}) + dt * S_i
        
        : F_{i+1/2} = F(U_i)
        """
        n = len(h)
        h_pred = h.copy()
        Q_pred = Q.copy()
        
        # ghost cells
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # 
        for i in range(1, n+1):  # ii
            # i
            cell_idx = i - 1  # 
            
            # 
            F_h_right = Q_ext[i]  # F_{i+1/2}
            F_h_left = Q_ext[i-1]  # F_{i-1/2}
            
            # Q
            A_i = max(h_ext[i] * self.B, self.eps_dry * self.B)
            A_im = max(h_ext[i-1] * self.B, self.eps_dry * self.B)
            
            F_Q_right = Q_ext[i]**2 / A_i + 0.5 * self.g * h_ext[i]**2 * self.B
            F_Q_left = Q_ext[i-1]**2 / A_im + 0.5 * self.g * h_ext[i-1]**2 * self.B
            
            # 
            S_h = 0.0
            S_Q = self._compute_source_term(h[cell_idx], Q[cell_idx])
            
            # 
            h_pred[cell_idx] = h[cell_idx] - dt/self.dx * (F_h_right - F_h_left) + dt * S_h
            Q_pred[cell_idx] = Q[cell_idx] - dt/self.dx * (F_Q_right - F_Q_left) + dt * S_Q
        
        return h_pred, Q_pred
    
    def _corrector_conservative(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        
        
        U_i** = U_i* - dt/dx * (F_{i+1/2} - F_{i-1/2}) + dt * S_i
        
        : F_{i-1/2} = F(U_i)
        """
        n = len(h)
        h_corr = h.copy()
        Q_corr = Q.copy()
        
        # 
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # 
        for i in range(1, n+1):
            cell_idx = i - 1
            
            # 
            F_h_right = Q_ext[i+1]
            F_h_left = Q_ext[i]
            
            A_i = max(h_ext[i] * self.B, self.eps_dry * self.B)
            A_ip = max(h_ext[i+1] * self.B, self.eps_dry * self.B)
            
            F_Q_right = Q_ext[i+1]**2 / A_ip + 0.5 * self.g * h_ext[i+1]**2 * self.B
            F_Q_left = Q_ext[i]**2 / A_i + 0.5 * self.g * h_ext[i]**2 * self.B
            
            # 
            S_h = 0.0
            S_Q = self._compute_source_term(h[cell_idx], Q[cell_idx])
            
            # 
            h_corr[cell_idx] = h[cell_idx] - dt/self.dx * (F_h_right - F_h_left) + dt * S_h
            Q_corr[cell_idx] = Q[cell_idx] - dt/self.dx * (F_Q_right - F_Q_left) + dt * S_Q
        
        return h_corr, Q_corr
    
    def _extend_with_ghosts(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        with ghost cells
        
        : [0, 1, ..., n-1]
        : [ghost_left, 0, 1, ..., n-1, ghost_right]
        """
        n = len(h)
        h_ext = np.zeros(n + 2)
        Q_ext = np.zeros(n + 2)
        
        # 
        h_ext[1:n+1] = h
        Q_ext[1:n+1] = Q
        
        # ghost
        if self.bc_left['type'] == 'h':
            h_ext[0] = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            Q_ext[0] = Q[0]  # 
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
    
    def _compute_source_term(self, h: float, Q: float) -> float:
        """"""
        A = max(h * self.B, self.eps_dry * self.B)
        P = self.B + 2.0 * h
        R = A / P if P > 1e-10 else 0.0
        
        if R > 1e-10 and abs(Q) > 1e-6:
            Sf = self.n**2 * Q**2 / (A**2 * R**(4.0/3.0))
            Sf = np.sign(Q) * Sf
        else:
            Sf = 0.0
        
        S = self.g * A * (self.S0 - Sf)
        return S
    
    def _enforce_boundary_conditions(self):
        """"""
        # 
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            self.h[0] = value if not callable(value) else value(self.t)
        elif self.bc_left['type'] == 'Q':
            value = self.bc_left['value']
            self.Q[0] = value if not callable(value) else value(self.t)
        
        # 
        if self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            self.h[-1] = value if not callable(value) else value(self.t)
        elif self.bc_right['type'] == 'Q':
            value = self.bc_right['value']
            self.Q[-1] = value if not callable(value) else value(self.t)
    
    def get_mass_conservation_error(self) -> float:
        """"""
        current_mass = np.sum(self.h * self.B * self.dx)
        if self.initial_mass > 1e-10:
            error = (current_mass - self.initial_mass) / self.initial_mass * 100.0
        else:
            error = 0.0
        return error
    
    def get_state(self) -> Dict:
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
    print("MacCormack v2.0 () - ")
    print("="*80)
    
    # Test: 
    print("\nTest:  - ")
    print("-"*80)
    
    solver = MacCormackSolverV2(
        width=10.0,
        length=1000.0,
        n_cells=50,
        manning_n=0.025,
        slope=0.001,
        cfl=0.8
    )
    
    # 
    h_init = np.ones(50) * 2.0
    Q_init = np.zeros(50)
    
    # 
    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 2.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 
    t_end = 300.0
    step_count = 0
    
    print(f"\n t={t_end}s:")
    while solver.t < t_end and step_count < 1000:
        solver.step()
        step_count += 1
        
        if step_count % 50 == 0:
            state = solver.get_state()
            print(f"  t={state['t']:6.1f}s, dt={state['dt']:.3f}s, "
                  f"={state['mass_error']:.6f}%, "
                  f"max|Q|={np.max(np.abs(state['Q'])):.6e}")
    
    # 
    state = solver.get_state()
    print(f"\n (n_steps={step_count}):")
    print(f"  : {state['mass_error']:.8f}%")
    print(f"  max|h-2.0|: {np.max(np.abs(state['h'] - 2.0)):.6e} m")
    print(f"  max|Q|: {np.max(np.abs(state['Q'])):.6e} m³/s")
    print(f"   < 0.5%: {'' if abs(state['mass_error']) < 0.5 else ''}")
    
    print("\n" + "="*80)
