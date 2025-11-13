#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacCormack - Saint-Venant

MacCormack:
-  +
-  
-  
-  CFL
-  

:
1. : U* = U^n - dt/dx * (F_{i+1} - F_i) + dt * S
2. : U** = U* - dt/dx * (F*_i - F*_{i-1}) + dt * S*
3. : U^{n+1} = 0.5 * (U^n + U**)

: HydroClaude Team
: 2025-10-28
"""

import numpy as np
from typing import Tuple, Optional, Callable
import warnings


class MacCormackSolver:
    """
    MacCormack
    
    Saint-Venant:
    ∂U/∂t + ∂F/∂x = S
    
    :
    U = [A, Q]^T = [h*B, Q]^T
    F = [Q, Q²/A + gI₁]^T
    S = [0, gA(S₀ - Sf)]^T
    
    I₁ = ∫h dB ≈ h²B/2 ()
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
        eps_dry: float = 1e-4,
        use_artificial_viscosity: bool = True,
        viscosity_coef: float = 0.3
    ):
        """
        
        
        Args:
            width:  (m)
            length:  (m)
            n_cells: 
            manning_n: Manning
            slope:  S₀
            g:  (m/s²)
            cfl: CFL0.3-0.7
            eps_dry: 
            use_artificial_viscosity: 
            viscosity_coef: 
        """
        self.B = width
        self.L = length
        self.n_cells = n_cells
        self.n_nodes = n_cells + 1
        self.dx = length / n_cells
        self.n = manning_n
        self.S0 = slope
        self.g = g
        self.cfl = cfl
        self.eps_dry = eps_dry
        self.use_artificial_viscosity = use_artificial_viscosity
        self.nu = viscosity_coef
        
        # 
        self.x = np.linspace(0, length, n_cells + 1)
        
        # 
        self.h = np.zeros(n_cells + 1)
        self.Q = np.zeros(n_cells + 1)
        
        # 
        self.t = 0.0
        self.dt = 0.0
        
        # 
        self.bc_upstream = None
        self.bc_downstream = None
        
        # 
        self.total_mass = 0.0
    
    def initialize(
        self,
        h_init: np.ndarray,
        Q_init: np.ndarray,
        bc_upstream: dict,
        bc_downstream: dict
    ):
        """
        
        
        Args:
            h_init:  [n_nodes]
            Q_init:  [n_nodes]
            bc_upstream:  {'type': 'h'|'Q', 'value': float|callable}
            bc_downstream: 
        """
        self.h = h_init.copy()
        self.Q = Q_init.copy()
        self.bc_upstream = bc_upstream
        self.bc_downstream = bc_downstream
        
        # 
        self.total_mass = self._compute_total_mass()
        
        print(f"MacCormack")
        print(f"  : {self.n_cells}, {self.n_nodes}")
        print(f"  dx = {self.dx:.2f} m")
        print(f"  : {self.total_mass:.2f} m³")
    
    def compute_dt(self) -> float:
        """
        CFL
        
        dt ≤ CFL * dx / (|u| + c)
        
        :
        u = Q/A: 
        c = √(gA/B): 
        """
        # 
        h_safe = np.maximum(self.h, self.eps_dry)
        A = h_safe * self.B
        
        # 
        u = self.Q / A
        
        # 
        c = np.sqrt(self.g * A / self.B)
        
        # 
        lambda_max = np.max(np.abs(u) + c)
        
        if lambda_max > 1e-10:
            dt = self.cfl * self.dx / lambda_max
        else:
            dt = 1.0  # 
        
        return dt
    
    def step(self, dt: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        MacCormack
        
        Args:
            dt: None
        
        Returns:
            (h, Q): 
        """
        if dt is None:
            dt = self.compute_dt()
        
        self.dt = dt
        
        # 
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        # ========== ==========
        h_pred, Q_pred = self._predictor_step(h_n, Q_n, dt)
        
        # ========== ==========
        h_corr, Q_corr = self._corrector_step(h_pred, Q_pred, dt)
        
        # ==========  ==========
        h_new = 0.5 * (h_n + h_corr)
        Q_new = 0.5 * (Q_n + Q_corr)
        
        # ========== ==========
        h_new, Q_new = self._apply_boundary_conditions(h_new, Q_new)
        
        # ========== ==========
        # 
        if self.use_artificial_viscosity and False:  # 
            h_new = self._apply_artificial_viscosity(h_new, self.nu)
            Q_new = self._apply_artificial_viscosity(Q_new, self.nu)
        
        # ==========  ==========
        h_new = np.maximum(h_new, 0.0)  # 0eps_dry
        
        # 
        self.h = h_new
        self.Q = Q_new
        self.t += dt
        
        return self.h.copy(), self.Q.copy()
    
    def _predictor_step(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        
        
        U* = U^n - dt/dx * (F_{i+1} - F_i) + dt * S_i
        """
        n = self.n_nodes
        
        # 
        F_h, F_Q = self._compute_flux(h, Q)
        S_h, S_Q = self._compute_source(h, Q)
        
        # 
        h_pred = h.copy()
        Q_pred = Q.copy()
        
        for i in range(1, n-1):
            # : ∂F/∂x ≈ (F_{i+1} - F_i) / dx
            dFh_dx = (F_h[i+1] - F_h[i]) / self.dx
            dFQ_dx = (F_Q[i+1] - F_Q[i]) / self.dx
            
            # 
            h_pred[i] = h[i] - dt * dFh_dx + dt * S_h[i]
            Q_pred[i] = Q[i] - dt * dFQ_dx + dt * S_Q[i]
        
        return h_pred, Q_pred
    
    def _corrector_step(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        
        
        U** = U* - dt/dx * (F*_i - F*_{i-1}) + dt * S*_i
        """
        n = self.n_nodes
        
        # 
        F_h, F_Q = self._compute_flux(h, Q)
        S_h, S_Q = self._compute_source(h, Q)
        
        # 
        h_corr = h.copy()
        Q_corr = Q.copy()
        
        for i in range(1, n-1):
            # : ∂F/∂x ≈ (F_i - F_{i-1}) / dx
            dFh_dx = (F_h[i] - F_h[i-1]) / self.dx
            dFQ_dx = (F_Q[i] - F_Q[i-1]) / self.dx
            
            # 
            h_corr[i] = h[i] - dt * dFh_dx + dt * S_h[i]
            Q_corr[i] = Q[i] - dt * dFQ_dx + dt * S_Q[i]
        
        return h_corr, Q_corr
    
    def _compute_flux(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        
        
        F = [F_h, F_Q]^T
        F_h = Q
        F_Q = Q²/A + gI₁
        
         I₁ = h²B/2 ()
        """
        # 
        h_safe = np.maximum(h, self.eps_dry)
        A = h_safe * self.B
        
        # 
        F_h = Q.copy()
        
        # 
        # Q²/A
        momentum_flux = Q**2 / A
        
        # : gI₁ = g * h²B / 2
        pressure = 0.5 * self.g * h_safe**2 * self.B
        
        F_Q = momentum_flux + pressure
        
        return F_h, F_Q
    
    def _compute_source(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        
        
        S = [S_h, S_Q]^T
        S_h = 0
        S_Q = gA(S₀ - Sf)
        
         Sf = n²Q²/(A²R^{4/3})
        """
        # 
        S_h = np.zeros_like(h)
        
        # 
        h_safe = np.maximum(h, self.eps_dry)
        A = h_safe * self.B
        
        # 
        P = self.B + 2.0 * h_safe
        
        # 
        R = A / P
        
        # 
        Sf = np.zeros_like(h)
        for i in range(len(h)):
            if R[i] > 1e-10 and abs(Q[i]) > 1e-6:
                Sf[i] = self.n**2 * Q[i]**2 / (A[i]**2 * R[i]**(4.0/3.0))
            else:
                Sf[i] = 0.0
        
        # Sf
        Sf = np.sign(Q) * np.abs(Sf)
        
        # 
        S_Q = self.g * A * (self.S0 - Sf)
        
        return S_h, S_Q
    
    def _apply_artificial_viscosity(
        self,
        U: np.ndarray,
        nu: float
    ) -> np.ndarray:
        """
        - 
        
        
        U_i^{new} = U_i - nu * [(U_i - U_{i-1}) - (U_{i+1} - U_i)]
                  = U_i + nu * (U_{i+1} - 2*U_i + U_{i-1})
        
        nu< 0.1
        """
        n = len(U)
        U_smooth = U.copy()
        
        # 
        for i in range(1, n-1):
            # 
            d2U = U[i+1] - 2.0*U[i] + U[i-1]
            U_smooth[i] = U[i] + nu * d2U
        
        return U_smooth
    
    def _apply_boundary_conditions(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """"""
        # 
        if self.bc_upstream['type'] == 'h':
            value = self.bc_upstream['value']
            h[0] = value(self.t) if callable(value) else value
        elif self.bc_upstream['type'] == 'Q':
            value = self.bc_upstream['value']
            Q[0] = value(self.t) if callable(value) else value
        
        # 
        if self.bc_downstream['type'] == 'h':
            value = self.bc_downstream['value']
            h[-1] = value(self.t) if callable(value) else value
        elif self.bc_downstream['type'] == 'Q':
            value = self.bc_downstream['value']
            Q[-1] = value(self.t) if callable(value) else value
        
        return h, Q
    
    def _compute_total_mass(self) -> float:
        """"""
        # 
        mass = 0.0
        for i in range(self.n_cells):
            h_avg = 0.5 * (self.h[i] + self.h[i+1])
            mass += h_avg * self.B * self.dx
        return mass
    
    def get_mass_conservation_error(self) -> float:
        """
        
        
        Returns:
             (%)
        """
        current_mass = self._compute_total_mass()
        if self.total_mass > 1e-10:
            error = (current_mass - self.total_mass) / self.total_mass * 100.0
        else:
            error = 0.0
        return error
    
    def get_state(self) -> dict:
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
    print("MacCormack - ")
    print("="*80)
    
    # ========== Test 1: ==========
    print("\n" + "="*80)
    print("Test 1:  - ")
    print("="*80)
    
    # 
    width = 10.0
    length = 1000.0
    n_cells = 50
    manning_n = 0.025
    slope = 0.001
    
    # 
    solver = MacCormackSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=manning_n,
        slope=slope,
        cfl=0.5
    )
    
    # 
    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)
    
    # 
    bc_upstream = {'type': 'h', 'value': 2.0}
    bc_downstream = {'type': 'h', 'value': 2.0}
    
    solver.initialize(h_init, Q_init, bc_upstream, bc_downstream)
    
    # 
    t_end = 600.0  # 10
    n_steps = 0
    
    print(f"\n t={t_end}s:")
    while solver.t < t_end:
        h, Q = solver.step()
        n_steps += 1
        
        if n_steps % 20 == 0:
            state = solver.get_state()
            print(f"  t={state['t']:6.1f}s, dt={state['dt']:.3f}s, "
                  f"max|Q|={np.max(np.abs(Q)):.6e}, "
                  f"={state['mass_error']:.6f}%")
    
    # 
    state = solver.get_state()
    print(f"\n (n_steps={n_steps}):")
    print(f"  : {state['mass_error']:.8f}%")
    print(f"  max|h-2.0|: {np.max(np.abs(state['h'] - 2.0)):.6e} m")
    print(f"  max|Q|: {np.max(np.abs(state['Q'])):.6e} m³/s")
    print(f"  :  < 0.1% {'' if abs(state['mass_error']) < 0.1 else ''}")
    
    print("\n" + "="*80)
    print("MacCormack")
    print("="*80)
