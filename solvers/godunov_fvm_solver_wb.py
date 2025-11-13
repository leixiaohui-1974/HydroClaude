#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM - Well-Balanced


1.  Well-Balanced MUSCL - 
2.  Strang splitting- 
3.  HLL - 
4.   - 

Order 2


- Audusse et al. (2004) "A Fast and Stable Well-Balanced Scheme"
- Zhou et al. (2001) "Surface Gradient Method"

: HydroClaude Team
: 2025-10-29
"""

import numpy as np
from typing import Tuple, Dict, Optional


class GodunvFVMSolverWB:
    """
    Well-Balanced Godunov-FVM
    
    
    1. Strang splitting
    2. Surface Gradient Method
    3. MUSCL
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
        order: int = 2,
        well_balanced: bool = True,
        entropy_fix: bool = False,
        critical_flow_treatment: bool = False
    ):
        """
        Well-Balanced

        Args:
            well_balanced: Well-Balanced
            entropy_fix: Harten-Hyman entropy
            critical_flow_treatment: 
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
        self.well_balanced = well_balanced
        self.entropy_fix = entropy_fix
        self.critical_flow_treatment = critical_flow_treatment
        
        # 
        self.h = np.zeros(n_cells)
        self.Q = np.zeros(n_cells)
        self.x = np.linspace(0.5*self.dx, length - 0.5*self.dx, n_cells)
        
        # 
        self.z_b = np.linspace(length * slope, 0.0, n_cells)
        
        # 
        self.t = 0.0
        self.dt = 0.0
        self.bc_left = None
        self.bc_right = None
        self.initial_mass = 0.0
        self.step_count = 0
        
        wb_status = "" if well_balanced else ""
        entropy_status = "" if entropy_fix else ""
        critical_status = "" if critical_flow_treatment else ""
        print(f"Godunov-FVM Well-Balanced:")
        print(f"  : {n_cells}, dx={self.dx:.3f}m")
        print(f"  : {order}")
        print(f"  Well-Balanced: {wb_status}")
        print(f"  Entropy Fix: {entropy_status}")
        print(f"  Critical Flow Treatment: {critical_status}")
        print(f"  : {slope}")
    
    def initialize(self, h_init, Q_init, bc_left, bc_right):
        """"""
        self.h = h_init.copy()
        self.Q = Q_init.copy()
        self.bc_left = bc_left
        self.bc_right = bc_right
        self.initial_mass = self._compute_total_mass()
        print(f"  : {self.initial_mass:.2f} m³")
    
    def compute_dt(self) -> float:
        """CFL"""
        h_safe = np.maximum(self.h, self.eps_dry)
        u = self.Q / (h_safe * self.B)
        c = np.sqrt(self.g * h_safe)
        lambda_max = np.max(np.abs(u) + c)
        return self.cfl * self.dx / lambda_max if lambda_max > 1e-10 else 1.0
    
    def step(self, dt: Optional[float] = None):
        """
        Well-Balanced
        
        Strang splitting:
        1. : S(dt/2)
        2. : C(dt)
        3. : S(dt/2)
        """
        if dt is None:
            dt = self.compute_dt()
        self.dt = dt
        
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        if self.well_balanced:
            # === Strang splitting ===
            # 1: 
            h_s1, Q_s1 = self._source_step(h_n, Q_n, dt/2.0)
            
            # 2: 
            h_c, Q_c = self._convection_step(h_s1, Q_s1, dt)
            
            # 3: 
            self.h, self.Q = self._source_step(h_c, Q_c, dt/2.0)
        else:
            # 
            self.h, self.Q = self._standard_step(h_n, Q_n, dt)
        
        # 
        self._apply_bc()
        
        # 
        self.h = np.maximum(self.h, 0.0)
        
        self.t += dt
        self.step_count += 1
        
        return self.h.copy(), self.Q.copy()
    
    def _source_step(self, h, Q, dt):
        """
        ODE
        
        dQ/dt = g*A*(S0 - Sf)
        
        Euler
        """
        h_new = h.copy()
        Q_new = Q.copy()
        
        for i in range(len(h)):
            A = max(h[i] * self.B, self.eps_dry * self.B)
            P = self.B + 2.0 * h[i]
            R = A / P if P > 1e-10 else 0.0
            
            if R > 1e-10 and abs(Q[i]) > 1e-6:
                # : Q^{n+1} = Q^n + dt * g*A*(S0 - Sf(Q^{n+1}))
                # dt
                Sf = self.n**2 * Q[i]**2 / (A**2 * R**(4.0/3.0))
                Sf = np.sign(Q[i]) * Sf
                
                S = self.g * A * (self.S0 - Sf)
                Q_new[i] = Q[i] + dt * S
            else:
                Q_new[i] = Q[i] + dt * self.g * A * self.S0
        
        return h_new, Q_new
    
    def _convection_step(self, h, Q, dt):
        """
        
        
        TVD-RK2 + Well-Balanced
        """
        # RK21
        dh_dt, dQ_dt = self._compute_convection_rhs(h, Q)
        h_star = h + dt * dh_dt
        Q_star = Q + dt * dQ_dt
        
        # 
        h_star, Q_star = self._apply_bc_to_state(h_star, Q_star)
        h_star = np.maximum(h_star, 0.0)
        
        # RK22
        dh_dt_star, dQ_dt_star = self._compute_convection_rhs(h_star, Q_star)
        h_new = 0.5 * (h + h_star) + 0.5 * dt * dh_dt_star
        Q_new = 0.5 * (Q + Q_star) + 0.5 * dt * dQ_dt_star
        
        return h_new, Q_new
    
    def _compute_convection_rhs(self, h, Q):
        """
        
        
        Well-Balanced
        """
        n = len(h)
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        # 
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # Well-Balancedsurface gradient method
        if self.order == 2 and self.well_balanced:
            # 
            eta = h + self.z_b  #  =  + 
            eta_ext = np.zeros(n + 2)
            eta_ext[1:n+1] = eta
            eta_ext[0] = eta[0]
            eta_ext[n+1] = eta[n-1]
            
            eta_L, eta_R = self._muscl_reconstruction(eta_ext)
            Q_L, Q_R = self._muscl_reconstruction(Q_ext)
            
            # 
            z_b_ext = np.zeros(n + 2)
            z_b_ext[1:n+1] = self.z_b
            z_b_ext[0] = self.z_b[0]
            z_b_ext[n+1] = self.z_b[-1]
            
            # 
            z_b_interfaces = np.zeros(n + 1)
            for i in range(n + 1):
                z_b_interfaces[i] = 0.5 * (z_b_ext[i] + z_b_ext[i+1])
            
            h_L = np.maximum(eta_L - z_b_interfaces, 0.0)
            h_R = np.maximum(eta_R - z_b_interfaces, 0.0)
        else:
            # 
            if self.order == 2:
                h_L, h_R = self._muscl_reconstruction(h_ext)
                Q_L, Q_R = self._muscl_reconstruction(Q_ext)
            else:
                h_L = h_ext[:-1]
                h_R = h_ext[1:]
                Q_L = Q_ext[:-1]
                Q_R = Q_ext[1:]
        
        # 
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)
        
        for i in range(n + 1):
            F_h[i], F_Q[i] = self._hll_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
        
        # 
        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx
        
        return dh_dt, dQ_dt
    
    def _standard_step(self, h, Q, dt):
        """"""
        # RK21
        dh_dt, dQ_dt = self._compute_rhs_with_source(h, Q)
        h_star = h + dt * dh_dt
        Q_star = Q + dt * dQ_dt
        
        h_star, Q_star = self._apply_bc_to_state(h_star, Q_star)
        h_star = np.maximum(h_star, 0.0)
        
        # RK22
        dh_dt_star, dQ_dt_star = self._compute_rhs_with_source(h_star, Q_star)
        h_new = 0.5 * (h + h_star) + 0.5 * dt * dh_dt_star
        Q_new = 0.5 * (Q + Q_star) + 0.5 * dt * dQ_dt_star
        
        return h_new, Q_new
    
    def _compute_rhs_with_source(self, h, Q):
        """+"""
        dh_dt, dQ_dt = self._compute_convection_rhs(h, Q)
        
        # 
        for i in range(len(h)):
            A = max(h[i] * self.B, self.eps_dry * self.B)
            P = self.B + 2.0 * h[i]
            R = A / P if P > 1e-10 else 0.0
            
            if R > 1e-10 and abs(Q[i]) > 1e-6:
                Sf = self.n**2 * Q[i]**2 / (A**2 * R**(4.0/3.0))
                Sf = np.sign(Q[i]) * Sf
            else:
                Sf = 0.0
            
            dQ_dt[i] += self.g * A * (self.S0 - Sf)
        
        return dh_dt, dQ_dt
    
    def _muscl_reconstruction(self, phi):
        """MUSCLMinmod"""
        n = len(phi) - 2
        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)
        
        def minmod(a, b):
            if a * b <= 0:
                return 0.0
            elif abs(a) < abs(b):
                return a
            else:
                return b
        
        for i in range(n + 1):
            # 
            if i > 0:
                slope_L = minmod(phi[i+1] - phi[i], phi[i] - phi[i-1])
                phi_L[i] = phi[i] + 0.5 * slope_L
            else:
                phi_L[i] = phi[i]
            
            # 
            if i < n:
                slope_R = minmod(phi[i+2] - phi[i+1], phi[i+1] - phi[i])
                phi_R[i] = phi[i+1] - 0.5 * slope_R
            else:
                phi_R[i] = phi[i+1]
        
        return phi_L, phi_R
    
    def _entropy_fix(self, lambda_val, delta):
        """
        Harten-Hyman Entropy

        

        :
            lambda_val: 
            delta: entropymax(|λ_L|, |λ_R|)10%

        :
            
        """
        if abs(lambda_val) >= delta:
            return lambda_val
        else:
            # 
            return (lambda_val**2 + delta**2) / (2.0 * delta)

    def _hll_flux(self, h_L, Q_L, h_R, Q_R):
        """
        HLL Riemannentropy

        :
            h_L, Q_L: 
            h_R, Q_R: 

        :
            F_h, F_Q: 
        """
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        # 
        A_L = max(h_L * self.B, self.eps_dry * self.B)
        u_L = Q_L / A_L
        c_L = np.sqrt(self.g * max(h_L, 0.0))

        A_R = max(h_R * self.B, self.eps_dry * self.B)
        u_R = Q_R / A_R
        c_R = np.sqrt(self.g * max(h_R, 0.0))

        # 
        S_L = min(u_L - c_L, u_R - c_R)
        S_R = max(u_L + c_L, u_R + c_R)

        # Entropy
        if self.entropy_fix:
            # delta10%
            delta = 0.1 * max(abs(S_L), abs(S_R), 1e-10)

            # entropy
            S_L = self._entropy_fix(S_L, delta)
            S_R = self._entropy_fix(S_R, delta)

        # 
        F_h_L = Q_L
        F_Q_L = Q_L**2 / A_L + 0.5 * self.g * h_L**2 * self.B

        F_h_R = Q_R
        F_Q_R = Q_R**2 / A_R + 0.5 * self.g * h_R**2 * self.B

        # HLL
        if S_L >= 0:
            # 
            F_h = F_h_L
            F_Q = F_Q_L
        elif S_R <= 0:
            # 
            F_h = F_h_R
            F_Q = F_Q_R
        else:
            # 
            U_h_L = h_L
            U_h_R = h_R
            U_Q_L = Q_L
            U_Q_R = Q_R

            F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
            F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)

        # 
        if self.critical_flow_treatment:
            # Froude
            Fr_L = abs(u_L) / c_L if c_L > 1e-10 else 0.0
            Fr_R = abs(u_R) / c_R if c_R > 1e-10 else 0.0

            # Froude
            Fr_avg = 0.5 * (Fr_L + Fr_R)

            # 0.9 < Fr < 1.1
            if 0.9 < Fr_avg < 1.1:
                # Fr=1
                # alphaFr=10.5Fr=0.91.10
                alpha = 0.5 * (1.0 - abs(Fr_avg - 1.0) / 0.1)

                # Lax-Friedrichs
                max_speed = max(abs(u_L) + c_L, abs(u_R) + c_R, 1e-10)

                # 
                dissipation_h = alpha * max_speed * (h_R - h_L)
                dissipation_Q = alpha * max_speed * (Q_R - Q_L)

                F_h -= dissipation_h
                F_Q -= dissipation_Q

        return F_h, F_Q
    
    def _extend_with_ghosts(self, h, Q):
        """ghost cells"""
        n = len(h)
        h_ext = np.zeros(n + 2)
        Q_ext = np.zeros(n + 2)
        
        h_ext[1:n+1] = h
        Q_ext[1:n+1] = Q
        
        # ghost
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            h_ext[0] = value if not callable(value) else value(self.t)
            Q_ext[0] = Q[0]
        elif self.bc_left['type'] == 'Q':
            h_ext[0] = h[0]
            value = self.bc_left['value']
            Q_ext[0] = value if not callable(value) else value(self.t)
        
        # ghost
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
    
    def _apply_bc(self):
        """"""
        self.h, self.Q = self._apply_bc_to_state(self.h, self.Q)

    def compute_froude_number(self, h=None, Q=None):
        """
        Froude

        Fr = u / sqrt(g*h)

        :
        - u = Q / (B*h)  
        - c = sqrt(g*h)  

        :
            h: self.h
            Q: self.Q

        :
            Fr: Froude
        """
        if h is None:
            h = self.h
        if Q is None:
            Q = self.Q

        Fr = np.zeros_like(h)

        for i in range(len(h)):
            if h[i] > self.eps_dry:
                u = Q[i] / (self.B * h[i])
                c = np.sqrt(self.g * h[i])
                Fr[i] = u / c if c > 1e-10 else 0.0
            else:
                Fr[i] = 0.0

        return Fr

    def is_critical_flow(self, Fr=None, threshold=0.1):
        """
        

        : |Fr - 1.0| < threshold

        :
            Fr: Froude
            threshold: 0.1

        :
            mask: True
        """
        if Fr is None:
            Fr = self.compute_froude_number()

        return np.abs(Fr - 1.0) < threshold

    def get_flow_regime(self, Fr=None):
        """
        

        :
            Fr: Froude

        :
            regime: 
                - 0:  (Fr < 0.9)
                - 1:  (0.9 <= Fr <= 1.1)
                - 2:  (Fr > 1.1)
        """
        if Fr is None:
            Fr = self.compute_froude_number()

        regime = np.zeros_like(Fr, dtype=int)
        regime[Fr < 0.9] = 0  # 
        regime[(Fr >= 0.9) & (Fr <= 1.1)] = 1  # 
        regime[Fr > 1.1] = 2  # 

        return regime

    def _compute_total_mass(self):
        """"""
        return np.sum(self.h * self.B * self.dx)
    
    def get_mass_conservation_error(self):
        """"""
        current_mass = self._compute_total_mass()
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
            'step': self.step_count,
            'mass_error': self.get_mass_conservation_error()
        }


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("="*80)
    print("Well-Balanced Godunov-FVM - ")
    print("="*80)
    
    # 
    print("\n:  (Well-Balanced)")
    from utils.canal_utils import compute_steady_uniform_flow
    
    solver = GodunvFVMSolverWB(
        width=10.0, length=1000.0, n_cells=100,
        manning_n=0.025, slope=0.001,
        cfl=0.5, order=2, well_balanced=True
    )
    
    h_uniform = compute_steady_uniform_flow(50.0, 10.0, 0.001, 0.025)
    h_init = np.ones(100) * h_uniform
    Q_init = np.ones(100) * 50.0
    
    bc_left = {'type': 'Q', 'value': 50.0}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 100
    for _ in range(100):
        solver.step()
    
    state = solver.get_state()
    print(f"\n (100):")
    print(f"  : {state['mass_error']:.6f}%")
    print(f"  : {abs(np.mean(state['h']) - h_uniform)/h_uniform*100:.2f}%")
    print(f"  : {'' if abs(state['mass_error']) < 1.0 else ''}")
    
    print("\n" + "="*80)
