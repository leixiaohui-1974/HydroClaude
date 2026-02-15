#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM - 


1.   - 
2.  
3.  
4.  


- 
- Riemann
- 

: HydroClaude Team
: 2025-10-29
"""

import logging
import numpy as np
from typing import Tuple, Dict, Optional, List
import sys, os

logger = logging.getLogger(__name__)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.gate import SluiceGate, BroadCrestedWeir


class GodunvFVMCoupled:
    """
    Godunov-FVM
    
    
    - SluiceGate
    - BroadCrestedWeir
    - 
    """
    
    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        structures: Optional[List] = None,
        g: float = 9.81,
        cfl: float = 0.5,
        eps_dry: float = 1e-6
    ):
        """
        
        
        Args:
            structures:  [SluiceGate, BroadCrestedWeir, ...]
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
        self.x = np.linspace(0.5*self.dx, length - 0.5*self.dx, n_cells)
        
        # 
        self.structures = structures if structures is not None else []
        
        # 
        self.structure_cells = []
        for struct in self.structures:
            idx = np.argmin(np.abs(self.x - struct.position))
            self.structure_cells.append(idx)
        
        self.t = 0.0
        self.dt = 0.0
        self.bc_left = None
        self.bc_right = None
        self.initial_mass = 0.0
        self.step_count = 0
        
        print(f"Godunov-FVM:")
        print(f"  : {n_cells}, dx={self.dx:.3f}m")
        print(f"  : {len(self.structures)}")
        for i, struct in enumerate(self.structures):
            print(f"    {i+1}. {struct.__class__.__name__} @ x={struct.position}m (#{self.structure_cells[i]})")
    
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
        """TVD-RK2"""
        if dt is None:
            dt = self.compute_dt()
        self.dt = dt
        
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        # RK21
        dh_dt, dQ_dt = self._compute_rhs(h_n, Q_n)
        h_star = h_n + dt * dh_dt
        Q_star = Q_n + dt * dQ_dt
        
        h_star, Q_star = self._apply_bc_to_state(h_star, Q_star)
        h_star = np.maximum(h_star, 0.0)
        
        # 
        h_star, Q_star = self._apply_structure_coupling(h_star, Q_star)
        
        # RK22
        dh_dt_star, dQ_dt_star = self._compute_rhs(h_star, Q_star)
        self.h = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt_star
        self.Q = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt_star
        
        self.h, self.Q = self._apply_bc_to_state(self.h, self.Q)
        self.h = np.maximum(self.h, 0.0)
        
        # 2
        self.h, self.Q = self._apply_structure_coupling(self.h, self.Q)
        
        self.t += dt
        self.step_count += 1
        
        return self.h.copy(), self.Q.copy()
    
    def _apply_structure_coupling(self, h, Q):
        """
        
        
        
        """
        for i, struct_idx in enumerate(self.structure_cells):
            struct = self.structures[i]
            
            # 
            if struct_idx > 0 and struct_idx < len(h) - 1:
                h_upstream = h[struct_idx - 1]
                h_downstream = h[struct_idx + 1]
                
                # 
                try:
                    Q_struct, flow_type = struct.calculate_discharge(
                        h_upstream, h_downstream, self.t
                    )
                    
                    # 
                    Q[struct_idx] = Q_struct
                    
                    # 
                    if struct_idx > 1:
                        Q[struct_idx - 1] = 0.7 * Q[struct_idx - 1] + 0.3 * Q_struct
                    if struct_idx < len(Q) - 2:
                        Q[struct_idx + 1] = 0.7 * Q[struct_idx + 1] + 0.3 * Q_struct
                        
                except Exception as e:
                    logger.warning(f"Structure coupling failed at cell {struct_idx} for {struct.__class__.__name__}: {e}")
        
        return h, Q
    
    def _compute_rhs(self, h, Q):
        """"""
        n = len(h)
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        
        # 
        h_L = h_ext[:-1]
        h_R = h_ext[1:]
        Q_L = Q_ext[:-1]
        Q_R = Q_ext[1:]
        
        # HLL
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)
        
        for i in range(n + 1):
            F_h[i], F_Q[i] = self._hll_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
        
        #  + 
        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx + self._compute_source_term(h[i], Q[i])
        
        return dh_dt, dQ_dt
    
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
    
    def _compute_source_term(self, h, Q):
        """"""
        A = max(h * self.B, self.eps_dry * self.B)
        P = self.B + 2.0 * h
        R = A / P if P > 1e-10 else 0.0
        
        if R > 1e-10 and abs(Q) > 1e-6:
            Sf = self.n**2 * Q**2 / (A**2 * R**(4.0/3.0))
            Sf = np.sign(Q) * Sf
        else:
            Sf = 0.0
        
        return self.g * A * (self.S0 - Sf)
    
    def _extend_with_ghosts(self, h, Q):
        """ghost cells"""
        n = len(h)
        h_ext = np.zeros(n + 2)
        Q_ext = np.zeros(n + 2)
        
        h_ext[1:n+1] = h
        Q_ext[1:n+1] = Q
        
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            h_ext[0] = value if not callable(value) else value(self.t)
            Q_ext[0] = Q[0]
        elif self.bc_left['type'] == 'Q':
            h_ext[0] = h[0]
            value = self.bc_left['value']
            Q_ext[0] = value if not callable(value) else value(self.t)
        
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
    
    def get_structure_info(self):
        """"""
        info = []
        for i, struct in enumerate(self.structures):
            idx = self.structure_cells[i]
            if idx > 0 and idx < len(self.h) - 1:
                h_us = self.h[idx - 1]
                h_ds = self.h[idx + 1]
                Q_struct = self.Q[idx]
                
                try:
                    Q_calc, flow_type = struct.calculate_discharge(h_us, h_ds, self.t)
                    opening = struct.get_opening(self.t) if hasattr(struct, 'get_opening') else None
                    
                    info.append({
                        'type': struct.__class__.__name__,
                        'position': struct.position,
                        'h_upstream': h_us,
                        'h_downstream': h_ds,
                        'Q_actual': Q_struct,
                        'Q_calculated': Q_calc,
                        'flow_type': flow_type,
                        'opening': opening
                    })
                except Exception as e:
                    logger.warning(f"Structure info retrieval failed for {struct.__class__.__name__} at cell {idx}: {e}")
                    info.append({'type': struct.__class__.__name__, 'error': True})
        
        return info


if __name__ == "__main__":
    from utils.canal_utils import compute_steady_uniform_flow
    
    print("="*80)
    print("Godunov-FVM - ")
    print("="*80)
    
    # 
    print("\n: ")
    
    width = 10.0
    length = 1000.0
    n_cells = 100
    Q_target = 30.0
    
    # 2m
    gate = SluiceGate(position=500.0, width=width, opening=2.0)
    
    solver = GodunvFVMCoupled(
        width=width, length=length, n_cells=n_cells,
        manning_n=0.025, slope=0.001,
        structures=[gate],
        cfl=0.5
    )
    
    # 
    h_uniform = compute_steady_uniform_flow(Q_target, width, 0.001, 0.025)
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q_target
    
    bc_left = {'type': 'Q', 'value': Q_target}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 
    print(f"\n500...")
    for _ in range(500):
        solver.step()
    
    state = solver.get_state()
    
    print(f"\n:")
    print(f"  : {state['mass_error']:.4f}%")
    print(f"  : {np.mean(state['Q']):.2f} m³/s")
    
    # 
    struct_info = solver.get_structure_info()
    if len(struct_info) > 0:
        info = struct_info[0]
        print(f"\n:")
        print(f"  : {info['position']}m")
        print(f"  : {info['h_upstream']:.3f}m")
        print(f"  : {info['h_downstream']:.3f}m")
        print(f"  : {info['Q_actual']:.2f}m³/s")
        print(f"  : {info['Q_calculated']:.2f}m³/s")
        print(f"  : {info['flow_type']}")
        print(f"  : {info['opening']:.2f}m")
    
    print(f"\n<1%: {'' if abs(state['mass_error']) < 1.0 else ''}")
    
    print("\n" + "="*80)
