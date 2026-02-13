#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM - Phase 0

Order 1
1.   - CFL + 
2.  Riemann - HLL + HLLC
3.   - 
4.   - 
5.   - 



: HydroClaude Team
: 2025-10-27
"""

import logging
import numpy as np
from typing import Tuple, Dict, Optional, List

logger = logging.getLogger(__name__)


class GodunvFVMProduction:
    """
    Godunov-FVMOrder 1
    
    
    1. CFL0.3
    2. 
    3. RiemannHLL+HLLC
    4. 
    5. <1%
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
        cfl: float = 0.3,
        eps_dry: float = 1e-4,
        riemann_solver: str = 'hybrid',
        artificial_viscosity: float = 0.05
    ):
        """
        
        
        Args:
            structures:  [SluiceGate, BroadCrestedWeir, ...]
            riemann_solver: 'HLL'(), 'HLLC'(), 'hybrid'()
            artificial_viscosity:  (0.05)
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
        self.riemann_solver = riemann_solver
        self.nu = artificial_viscosity
        
        # 
        self.h = np.zeros(n_cells)
        self.Q = np.zeros(n_cells)
        self.x = np.linspace(0.5*self.dx, length - 0.5*self.dx, n_cells)
        
        # 
        self.structures = structures if structures is not None else []
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
        
        print(f"[ROCKET] Godunov-FVM (Phase 0)")
        print(f"  : {n_cells}, dx={self.dx:.3f}m")
        print(f"  CFL: {cfl} ()")
        print(f"  Riemann: {riemann_solver}")
        print(f"  : {artificial_viscosity}")
        print(f"  : {len(self.structures)}")
    
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
        return 0.1
    
    def step(self, dt: Optional[float] = None):
        """"""
        if dt is None:
            dt = self.compute_dt()
        self.dt = dt
        
        h_n = self.h.copy()
        Q_n = self.Q.copy()
        
        # === Stage 1 ===
        dh_dt, dQ_dt = self._compute_rhs(h_n, Q_n)
        h_star = h_n + dt * dh_dt
        Q_star = Q_n + dt * dQ_dt
        
        # 
        Q_star = self._semi_implicit_friction(h_star, Q_star, dt)
        
        h_star, Q_star = self._apply_bc(h_star, Q_star)
        h_star = np.maximum(h_star, 0.0)
        
        # 
        if len(self.structures) > 0:
            h_star, Q_star = self._apply_structure_coupling(h_star, Q_star)
        
        # === Stage 2 ===
        dh_dt_star, dQ_dt_star = self._compute_rhs(h_star, Q_star)
        self.h = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt_star
        self.Q = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt_star
        
        # 2
        self.Q = self._semi_implicit_friction(self.h, self.Q, dt)
        
        self.h, self.Q = self._apply_bc(self.h, self.Q)
        self.h = np.maximum(self.h, 0.0)
        
        # 2
        if len(self.structures) > 0:
            self.h, self.Q = self._apply_structure_coupling(self.h, self.Q)
        
        # 10
        if self.step_count % 10 == 0 and self.nu > 0.0:
            self.h, self.Q = self._apply_smoothing(self.h, self.Q)
        
        self.t += dt
        self.step_count += 1
        
        return self.h.copy(), self.Q.copy()
    
    def _compute_rhs(self, h, Q):
        """"""
        n = len(h)
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        h_ext, Q_ext = self._extend_ghosts(h, Q)
        
        # Order 1
        h_L = h_ext[:-1]
        h_R = h_ext[1:]
        Q_L = Q_ext[:-1]
        Q_R = Q_ext[1:]
        
        # Riemann
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)
        
        for i in range(n + 1):
            if self.riemann_solver == 'hybrid':
                # 
                if self._is_shock(h_L[i], h_R[i]):
                    F_h[i], F_Q[i] = self._hllc_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
                else:
                    F_h[i], F_Q[i] = self._hll_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
            elif self.riemann_solver == 'HLLC':
                F_h[i], F_Q[i] = self._hllc_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
            else:
                F_h[i], F_Q[i] = self._hll_flux(h_L[i], Q_L[i], h_R[i], Q_R[i])
        
        #  + 
        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            
            # 
            A = max(h[i] * self.B, self.eps_dry * self.B)
            S_g = self.g * A * self.S0
            
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx + S_g
        
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
            U_h_L, U_h_R = h_L, h_R
            U_Q_L, U_Q_R = Q_L, Q_R
            
            F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
            F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)
            
            return F_h, F_Q
    
    def _hllc_flux(self, h_L, Q_L, h_R, Q_R):
        """HLLC Riemann"""
        # HLLC
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0
        
        # HLL
        if self.n > 0.0:
            u_avg = 0.5 * (Q_L / max(h_L * self.B, self.eps_dry * self.B) + 
                           Q_R / max(h_R * self.B, self.eps_dry * self.B))
            if abs(u_avg) < 0.5:  # HLL
                return self._hll_flux(h_L, Q_L, h_R, Q_R)
        
        A_L = max(h_L * self.B, self.eps_dry * self.B)
        u_L = Q_L / A_L
        c_L = np.sqrt(self.g * max(h_L, self.eps_dry))
        
        A_R = max(h_R * self.B, self.eps_dry * self.B)
        u_R = Q_R / A_R
        c_R = np.sqrt(self.g * max(h_R, self.eps_dry))
        
        S_L = min(u_L - c_L, u_R - c_R)
        S_R = max(u_L + c_L, u_R + c_R)
        
        # 
        denom = (h_L * (S_L - u_L) - h_R * (S_R - u_R))
        if abs(denom) < 1e-10:
            return self._hll_flux(h_L, Q_L, h_R, Q_R)
        
        S_M = (Q_L - Q_R + h_R * self.B * (S_R - u_R) - h_L * self.B * (S_L - u_L)) / (denom * self.B)
        
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
            coef = (S_L - u_L) / (S_L - S_M)
            h_L_star = h_L * coef
            Q_L_star = h_L_star * S_M * self.B
            
            F_h = F_h_L + S_L * (h_L_star - h_L)
            F_Q = F_Q_L + S_L * (Q_L_star - Q_L)
            return F_h, F_Q
        else:
            # *
            coef = (S_R - u_R) / (S_R - S_M)
            h_R_star = h_R * coef
            Q_R_star = h_R_star * S_M * self.B
            
            F_h = F_h_R + S_R * (h_R_star - h_R)
            F_Q = F_Q_R + S_R * (Q_R_star - Q_R)
            return F_h, F_Q
    
    def _is_shock(self, h_L, h_R):
        """>15%"""
        h_avg = 0.5 * (h_L + h_R)
        if h_avg < self.eps_dry:
            return False
        gradient = abs(h_R - h_L) / h_avg
        return gradient > 0.15
    
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
                K = self.g * self.n**2 * abs(Q[i]) / (A**2 * R**(4.0/3.0))
                Q_new[i] = Q[i] / (1.0 + dt * K)
        
        return Q_new
    
    def _apply_structure_coupling(self, h, Q):
        """"""
        for i, idx in enumerate(self.structure_cells):
            struct = self.structures[i]
            
            if idx <= 0 or idx >= len(h) - 1:
                continue
            
            # 
            if idx >= 2:
                h_us = 0.5 * (h[idx-1] + h[idx-2])
            else:
                h_us = h[idx-1]
            
            if idx <= len(h) - 3:
                h_ds = 0.5 * (h[idx+1] + h[idx+2])
            else:
                h_ds = h[idx+1]
            
            try:
                Q_struct, _ = struct.calculate_discharge(h_us, h_ds, self.t)
                
                # 
                alpha = 0.2  # 
                Q[idx] = (1 - alpha) * Q[idx] + alpha * Q_struct
                
                # 
                if idx > 0:
                    Q[idx-1] = (1 - 0.5*alpha) * Q[idx-1] + 0.5*alpha * Q_struct
                if idx < len(Q) - 1:
                    Q[idx+1] = (1 - 0.5*alpha) * Q[idx+1] + 0.5*alpha * Q_struct
            except Exception as e:
                logger.warning(f"Structure coupling failed at cell {idx} for {struct.__class__.__name__}: {e}")

        return h, Q
    
    def _apply_smoothing(self, h, Q):
        """"""
        if self.nu <= 0.0:
            return h, Q
        
        h_smooth = h.copy()
        Q_smooth = Q.copy()
        
        # 
        for i in range(1, len(h) - 1):
            h_smooth[i] = h[i] + self.nu * (h[i-1] - 2*h[i] + h[i+1])
            Q_smooth[i] = Q[i] + self.nu * (Q[i-1] - 2*Q[i] + Q[i+1])
        
        return h_smooth, Q_smooth
    
    def _extend_ghosts(self, h, Q):
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
    
    def _apply_bc(self, h, Q):
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
        """%"""
        current_mass = np.sum(self.h * self.B * self.dx)
        if self.initial_mass > 1e-10:
            return (current_mass - self.initial_mass) / self.initial_mass * 100.0
        return 0.0
    
    def get_uniformity(self):
        """%"""
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
    
    def get_structure_info(self):
        """"""
        info = []
        for i, idx in enumerate(self.structure_cells):
            struct = self.structures[i]
            if idx > 0 and idx < len(self.h) - 1:
                try:
                    h_us = self.h[idx-1]
                    h_ds = self.h[idx+1]
                    Q_calc, flow_type = struct.calculate_discharge(h_us, h_ds, self.t)
                    opening = struct.get_opening(self.t) if hasattr(struct, 'get_opening') else None
                    
                    info.append({
                        'type': struct.__class__.__name__,
                        'position': struct.position,
                        'h_upstream': h_us,
                        'h_downstream': h_ds,
                        'Q_actual': self.Q[idx],
                        'Q_calculated': Q_calc,
                        'flow_type': flow_type,
                        'opening': opening
                    })
                except Exception as e:
                    logger.warning(f"Structure info retrieval failed for {struct.__class__.__name__} at cell {idx}: {e}")
                    info.append({'type': struct.__class__.__name__, 'error': True})
        return info


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/workspace')
    from utils.canal_utils import compute_steady_uniform_flow
    from solvers.gate import SluiceGate
    
    print("="*80)
    print("Phase 0 - ")
    print("="*80)
    
    # 1: 
    print("\n1 - ")
    
    solver1 = GodunvFVMProduction(
        width=10.0, length=1000.0, n_cells=100,
        manning_n=0.025, slope=0.001,
        cfl=0.3, riemann_solver='HLL', artificial_viscosity=0.05
    )
    
    Q_target = 50.0
    h_uniform = compute_steady_uniform_flow(Q_target, 10.0, 0.001, 0.025)
    h_init = np.ones(100) * h_uniform
    Q_init = np.ones(100) * Q_target
    
    bc_left = {'type': 'Q', 'value': Q_target}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver1.initialize(h_init, Q_init, bc_left, bc_right)
    
    for _ in range(500):
        solver1.step()
    
    state1 = solver1.get_state()
    print(f"\n:")
    print(f"  : {state1['mass_error']:.4f}% (<0.5%)")
    print(f"  : {state1['uniformity']:.2f}% (<5%)")
    print(f"  : {abs(np.mean(state1['h']) - h_uniform)/h_uniform*100:.4f}%")
    
    passed_1 = abs(state1['mass_error']) < 0.5 and state1['uniformity'] < 5.0
    print(f"\n{'' if passed_1 else ''} 1: {'' if passed_1 else ''}")
    
    # 2: 
    print("\n" + "="*80)
    print("2 - ")
    
    gate = SluiceGate(position=500.0, width=10.0, opening=2.0)
    
    solver2 = GodunvFVMProduction(
        width=10.0, length=1000.0, n_cells=100,
        manning_n=0.025, slope=0.001,
        structures=[gate],
        cfl=0.3, riemann_solver='HLL', artificial_viscosity=0.05
    )
    
    solver2.initialize(h_init, Q_init, bc_left, bc_right)
    
    for _ in range(500):
        solver2.step()
    
    state2 = solver2.get_state()
    struct_info = solver2.get_structure_info()[0]
    
    print(f"\n:")
    print(f"  : {state2['mass_error']:.4f}% (<1%)")
    print(f"  : {abs(struct_info['Q_actual'] - struct_info['Q_calculated'])/struct_info['Q_calculated']*100:.2f}%")
    
    passed_2 = abs(state2['mass_error']) < 1.0
    print(f"\n{'' if passed_2 else ''} 2: {'' if passed_2 else ''}")
    
    # 
    print("\n" + "="*80)
    print("[TARGET] Phase 0")
    print("="*80)
    print(f" 1 (Order 2): Order 1")
    print(f"{'' if passed_1 else ''} 2 (): {'' if passed_1 else ''}")
    print(f" 3 (Riemann): ")
    print(f"{'' if passed_2 else ''} 4 (): {'' if passed_2 else ''}")
    print(f"⏳ 5 (): ")
    
    if passed_1 and passed_2:
        print(f"\n[SUCCESS] Phase 0")
    else:
        print(f"\n[WARN] ")
