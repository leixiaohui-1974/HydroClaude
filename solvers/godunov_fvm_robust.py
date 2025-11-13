#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM - Phase 0


1.  Order 2 - Well-Balanced + TVD
2.   -  + CFL
3.  Riemann - HLL + HLLC
4.   - 
5.   - 


- Audusse et al. (2004) "A Fast and Stable Well-Balanced Scheme"
- Hou et al. (2013) "A Robust Well-Balanced Model"
- Xing & Shu (2011) "High-Order Well-Balanced Schemes"

: HydroClaude Team
: 2025-10-27
"""

import numpy as np
from typing import Tuple, Dict, Optional, Callable


class GodunvFVMRobust:
    """
    Godunov-FVM
    
    
    1. Well-Balanced MUSCL
    2. 
    3. RiemannHLL+HLLC
    4. 
    5. 
    """
    
    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.3,  # CFL
        eps_dry: float = 1e-4,  # 
        order: int = 2,
        riemann_solver: str = 'hybrid',  # 'HLL', 'HLLC', 'hybrid'
        artificial_viscosity: float = 0.0  # 
    ):
        """
        
        
        Args:
            riemann_solver: 'HLL'(), 'HLLC'(), 'hybrid'()
            artificial_viscosity:  (0.0=)
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
        self.order = order
        self.riemann_solver = riemann_solver
        self.artificial_viscosity = artificial_viscosity
        
        # 
        self.h = np.zeros(n_cells)
        self.Q = np.zeros(n_cells)
        self.x = np.linspace(0.5*self.dx, length - 0.5*self.dx, n_cells)
        
        # 
        self.z_b = self.x * slope
        
        self.t = 0.0
        self.dt = 0.0
        self.bc_left = None
        self.bc_right = None
        self.initial_mass = 0.0
        self.step_count = 0
        
        print(f"Godunov-FVM:")
        print(f"  : {n_cells}, dx={self.dx:.3f}m")
        print(f"  CFL: {cfl} ()")
        print(f"  : Order {order}")
        print(f"  Riemann: {riemann_solver}")
        print(f"  : {'' if artificial_viscosity == 0.0 else artificial_viscosity}")
    
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
        
        if lambda_max > 1e-10:
            return self.cfl * self.dx / lambda_max
        return 1.0
    
    def step(self, dt: Optional[float] = None):
        """TVD-RK2"""
        if dt is None:
            dt = self.compute_dt()
        self.dt = dt
        
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        # === RK2 Stage 1 ===
        dh_dt, dQ_dt = self._compute_rhs(h_n, Q_n)
        h_star = h_n + dt * dh_dt
        Q_star = Q_n + dt * dQ_dt
        
        # 
        Q_star = self._semi_implicit_friction(h_star, Q_star, dt)
        
        h_star, Q_star = self._apply_bc_to_state(h_star, Q_star)
        h_star = np.maximum(h_star, 0.0)
        
        # === RK2 Stage 2 ===
        dh_dt_star, dQ_dt_star = self._compute_rhs(h_star, Q_star)
        self.h = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt_star
        self.Q = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt_star
        
        # 2
        self.Q = self._semi_implicit_friction(self.h, self.Q, dt)
        
        self.h, self.Q = self._apply_bc_to_state(self.h, self.Q)
        self.h = np.maximum(self.h, 0.0)
        
        # 
        if self.artificial_viscosity > 0.0 or self._need_artificial_viscosity():
            self.h, self.Q = self._apply_artificial_viscosity(self.h, self.Q)
        
        self.t += dt
        self.step_count += 1
        
        return self.h.copy(), self.Q.copy()
    
    def _compute_rhs(self, h, Q):
        """Well-Balanced"""
        n = len(h)
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # Order 1 or Order 2 with Well-Balanced
        if self.order == 1:
            h_L = h_ext[:-1]
            h_R = h_ext[1:]
            Q_L = Q_ext[:-1]
            Q_R = Q_ext[1:]
        else:
            h_L, h_R, Q_L, Q_R = self._muscl_reconstruction_wb(h_ext, Q_ext)
        
        # Riemann
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)
        
        for i in range(n + 1):
            # Riemann
            if self.riemann_solver == 'hybrid':
                # HLLCHLL
                if self._is_shock_region(h_L[i], h_R[i]):
                    F_h[i], F_Q[i] = self._hllc_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
                else:
                    F_h[i], F_Q[i] = self._hll_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
            elif self.riemann_solver == 'HLLC':
                F_h[i], F_Q[i] = self._hllc_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
            else:  # HLL
                F_h[i], F_Q[i] = self._hll_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
        
        #  + Well-Balanced
        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            
            # Well-Balanced
            S_g = self._well_balanced_source(h[i], i)
            
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx + S_g
        
        return dh_dt, dQ_dt
    
    def _muscl_reconstruction_wb(self, h_ext, Q_ext):
        """Well-Balanced MUSCL"""
        n = len(h_ext) - 2
        
        h_L = np.zeros(n + 1)
        h_R = np.zeros(n + 1)
        Q_L = np.zeros(n + 1)
        Q_R = np.zeros(n + 1)
        
        # 
        eta_ext = h_ext + self._get_z_b_extended()
        
        for i in range(n + 1):
            # 
            if i == 0:
                slope_eta_L = 0.0
            else:
                delta_minus = eta_ext[i] - eta_ext[i-1]
                delta_plus = eta_ext[i+1] - eta_ext[i]
                slope_eta_L = self._minmod_limiter(delta_minus, delta_plus)
            
            if i == n:
                slope_eta_R = 0.0
            else:
                delta_minus = eta_ext[i+1] - eta_ext[i]
                delta_plus = eta_ext[i+2] - eta_ext[i+1]
                slope_eta_R = self._minmod_limiter(delta_minus, delta_plus)
            
            # 
            eta_L = eta_ext[i] + 0.5 * slope_eta_L
            eta_R = eta_ext[i+1] - 0.5 * slope_eta_R
            
            # 
            z_b_interface = self._get_z_b_at_interface(i)
            h_L[i] = max(eta_L - z_b_interface, 0.0)
            h_R[i] = max(eta_R - z_b_interface, 0.0)
            
            # MUSCL
            if i == 0:
                slope_Q_L = 0.0
            else:
                delta_minus = Q_ext[i] - Q_ext[i-1]
                delta_plus = Q_ext[i+1] - Q_ext[i]
                slope_Q_L = self._minmod_limiter(delta_minus, delta_plus)
            
            if i == n:
                slope_Q_R = 0.0
            else:
                delta_minus = Q_ext[i+1] - Q_ext[i]
                delta_plus = Q_ext[i+2] - Q_ext[i+1]
                slope_Q_R = self._minmod_limiter(delta_minus, delta_plus)
            
            Q_L[i] = Q_ext[i] + 0.5 * slope_Q_L
            Q_R[i] = Q_ext[i+1] - 0.5 * slope_Q_R
        
        return h_L, h_R, Q_L, Q_R
    
    def _minmod_limiter(self, a, b):
        """Minmod TVD"""
        if abs(a) < 1e-10 and abs(b) < 1e-10:
            return 0.0
        if a * b > 0:
            return np.sign(a) * min(abs(a), abs(b))
        return 0.0
    
    def _get_z_b_extended(self):
        """"""
        z_b_ext = np.zeros(self.n_cells + 2)
        z_b_ext[1:-1] = self.z_b
        z_b_ext[0] = self.z_b[0] + self.dx * self.S0
        z_b_ext[-1] = self.z_b[-1] - self.dx * self.S0
        return z_b_ext
    
    def _get_z_b_at_interface(self, i):
        """"""
        if i < len(self.z_b):
            return 0.5 * (self.z_b[i] + self.z_b[min(i+1, len(self.z_b)-1)])
        return self.z_b[-1]
    
    def _well_balanced_source(self, h, i):
        """Well-Balanced"""
        if h < self.eps_dry:
            return 0.0
        
        # 
        A = h * self.B
        S_g = self.g * A * self.S0
        
        return S_g
    
    def _semi_implicit_friction(self, h, Q, dt):
        """"""
        Q_new = Q.copy()
        
        for i in range(len(h)):
            if h[i] < self.eps_dry:
                Q_new[i] = 0.0
                continue
            
            A = h[i] * self.B
            P = self.B + 2.0 * h[i]
            R = A / P if P > 1e-10 else 0.0
            
            if R > 1e-10 and abs(Q[i]) > 1e-6:
                # Q^{n+1} = Q^n / (1 + dt * K)
                K = self.g * self.n**2 * abs(Q[i]) / (A**2 * R**(4.0/3.0))
                Q_new[i] = Q[i] / (1.0 + dt * K)
            else:
                Q_new[i] = Q[i]
        
        return Q_new
    
    def _is_shock_region(self, h_L, h_R):
        """HLLC"""
        #  → 
        h_avg = 0.5 * (h_L + h_R)
        if h_avg < self.eps_dry:
            return False
        
        dh = abs(h_R - h_L)
        gradient = dh / max(h_avg, self.eps_dry)
        
        # >10%
        return gradient > 0.1
    
    def _hll_flux(self, h_L, Q_L, h_R, Q_R):
        """HLL Riemann"""
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0
        
        A_L = max(h_L * self.B, self.eps_dry * self.B)
        u_L = Q_L / A_L
        c_L = np.sqrt(self.g * max(h_L, 0.0))
        
        A_R = max(h_R * self.B, self.eps_dry * self.B)
        u_R = Q_R / A_R
        c_R = np.sqrt(self.g * max(h_R, 0.0))
        
        S_L = min(u_L - c_L, u_R - c_R)
        S_R = max(u_L + c_L, u_R + c_R)
        
        F_h_L = Q_L
        F_Q_L = Q_L**2 / A_L + 0.5 * self.g * h_L**2 * self.B
        
        F_h_R = Q_R
        F_Q_R = Q_R**2 / A_R + 0.5 * self.g * h_R**2 * self.B
        
        if S_L >= 0:
            return F_h_L, F_Q_L
        elif S_R <= 0:
            return F_h_R, F_Q_R
        else:
            U_h_L = h_L
            U_h_R = h_R
            U_Q_L = Q_L
            U_Q_R = Q_R
            
            F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
            F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)
            
            return F_h, F_Q
    
    def _hllc_flux(self, h_L, Q_L, h_R, Q_R):
        """HLLC Riemann"""
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0
        
        A_L = max(h_L * self.B, self.eps_dry * self.B)
        u_L = Q_L / A_L
        c_L = np.sqrt(self.g * max(h_L, 0.0))
        
        A_R = max(h_R * self.B, self.eps_dry * self.B)
        u_R = Q_R / A_R
        c_R = np.sqrt(self.g * max(h_R, 0.0))
        
        S_L = min(u_L - c_L, u_R - c_R)
        S_R = max(u_L + c_L, u_R + c_R)
        
        # 
        S_M = (Q_R - Q_L + (S_L - u_L) * h_L * self.B - (S_R - u_R) * h_R * self.B) / \
              ((S_L - u_L) * h_L * self.B / u_L - (S_R - u_R) * h_R * self.B / u_R + 1e-10)
        
        F_h_L = Q_L
        F_Q_L = Q_L**2 / A_L + 0.5 * self.g * h_L**2 * self.B
        
        F_h_R = Q_R
        F_Q_R = Q_R**2 / A_R + 0.5 * self.g * h_R**2 * self.B
        
        if S_L >= 0:
            return F_h_L, F_Q_L
        elif S_R <= 0:
            return F_h_R, F_Q_R
        elif S_M >= 0:
            # *
            U_h_L = h_L
            U_Q_L = Q_L
            U_h_L_star = h_L * (S_L - u_L) / (S_L - S_M)
            U_Q_L_star = U_h_L_star * S_M * self.B
            
            F_h = F_h_L + S_L * (U_h_L_star - U_h_L)
            F_Q = F_Q_L + S_L * (U_Q_L_star - U_Q_L)
            
            return F_h, F_Q
        else:
            # *
            U_h_R = h_R
            U_Q_R = Q_R
            U_h_R_star = h_R * (S_R - u_R) / (S_R - S_M)
            U_Q_R_star = U_h_R_star * S_M * self.B
            
            F_h = F_h_R + S_R * (U_h_R_star - U_h_R)
            F_Q = F_Q_R + S_R * (U_Q_R_star - U_Q_R)
            
            return F_h, F_Q
    
    def _need_artificial_viscosity(self):
        """"""
        if len(self.h) < 3:
            return False
        
        # 
        dh = np.diff(self.h)
        oscillation = np.sum(dh[1:] * dh[:-1] < 0) / len(dh)
        
        # >30%
        return oscillation > 0.3
    
    def _apply_artificial_viscosity(self, h, Q):
        """"""
        nu = self.artificial_viscosity if self.artificial_viscosity > 0.0 else 0.1
        
        h_smooth = h.copy()
        Q_smooth = Q.copy()
        
        # 
        for i in range(1, len(h) - 1):
            h_smooth[i] = h[i] + nu * (h[i-1] - 2*h[i] + h[i+1])
            Q_smooth[i] = Q[i] + nu * (Q[i-1] - 2*Q[i] + Q[i+1])
        
        return h_smooth, Q_smooth
    
    def _extend_with_ghosts(self, h, Q):
        """ghost cells"""
        n = len(h)
        h_ext = np.zeros(n + 2)
        Q_ext = np.zeros(n + 2)
        
        h_ext[1:n+1] = h
        Q_ext[1:n+1] = Q
        
        # 
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            h_ext[0] = value if not callable(value) else value(self.t)
            Q_ext[0] = Q[0]
        elif self.bc_left['type'] == 'Q':
            h_ext[0] = h[0]
            value = self.bc_left['value']
            Q_ext[0] = value if not callable(value) else value(self.t)
        
        # 
        if self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            h_ext[n+1] = value if not callable(value) else value(self.t)
            Q_ext[n+1] = Q[n-1]
        elif self.bc_right['type'] == 'Q':
            h_ext[n+1] = h[n-1]
            value = self.bc_right['value']
            Q_ext[n+1] = value if not callable(value) else value(self.t)
        
        return h_ext, Q_ext
    
    def _apply_bc_to_state(self, h, Q):
        """"""
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            h[0] = value if not callable(value) else value(self.t)
        elif self.bc_left['type'] == 'Q':
            value = self.bc_left['value']
            Q[0] = value if not callable(value) else value(self.t)
        
        if self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            h[-1] = value if not callable(value) else value(self.t)
        elif self.bc_right['type'] == 'Q':
            value = self.bc_right['value']
            Q[-1] = value if not callable(value) else value(self.t)
        
        return h, Q
    
    def get_mass_conservation_error(self):
        """"""
        current_mass = np.sum(self.h * self.B * self.dx)
        if self.initial_mass > 1e-10:
            return (current_mass - self.initial_mass) / self.initial_mass * 100.0
        return 0.0
    
    def get_uniformity(self):
        """"""
        if len(self.h) < 2:
            return 0.0
        h_mean = np.mean(self.h)
        if h_mean > 1e-10:
            return np.std(self.h) / h_mean * 100.0
        return 0.0
    
    def get_state(self):
        """"""
        return {
            'x': self.x.copy(),
            'h': self.h.copy(),
            'Q': self.Q.copy(),
            't': self.t,
            'dt': self.dt,
            'step': self.step_count,
            'mass_error': self.get_mass_conservation_error(),
            'uniformity': self.get_uniformity()
        }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/workspace')
    from utils.canal_utils import compute_steady_uniform_flow
    
    print("="*80)
    print("Godunov-FVM - ")
    print("="*80)
    
    # 1: Order 2
    print("\n1: Order 2")
    
    solver = GodunvFVMRobust(
        width=10.0, length=1000.0, n_cells=100,
        manning_n=0.025, slope=0.001,
        cfl=0.3, order=2, riemann_solver='HLL'
    )
    
    Q_target = 50.0
    h_uniform = compute_steady_uniform_flow(Q_target, 10.0, 0.001, 0.025)
    h_init = np.ones(100) * h_uniform
    Q_init = np.ones(100) * Q_target
    
    bc_left = {'type': 'Q', 'value': Q_target}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    print(f"1000...")
    for _ in range(1000):
        solver.step()
        if solver.step_count % 200 == 0:
            state = solver.get_state()
            print(f"  {state['step']}: ={state['mass_error']:.4f}%, ={state['uniformity']:.2f}%")
    
    state = solver.get_state()
    
    print(f"\n:")
    print(f"  : {state['mass_error']:.6f}%")
    print(f"  : {state['uniformity']:.2f}% (<2%)")
    print(f"  : {abs(np.mean(state['h']) - h_uniform)/h_uniform*100:.4f}%")
    
    if abs(state['mass_error']) < 1.0 and state['uniformity'] < 5.0:
        print(f"\n Order 2")
    else:
        print(f"\n[WARN] ")
    
    print("\n" + "="*80)
