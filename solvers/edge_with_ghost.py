#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ghost Cells

Phase 2: Ghost Cell
- 
- ghost cells
- FVM

: HydroClaude Team
: 2025-10-27
"""

import numpy as np
from typing import Tuple, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EdgeWithGhostCells:
    """
    Ghost Cells
    
    :
        [ghost_left] + [interior cells] + [ghost_right]
         ↑             ↑                  ↑
         [0]          [1] to [n_cells]   [n_cells+1]
    
    :
    - ghost cells
    - ghost cells
    - FVM
    """
    
    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        cfl: float = 0.5,
        g: float = 9.81
    ):
        """
        ghost cells
        
        Args:
            width: (m)
            length: (m)
            n_cells: 
            manning_n: 
            slope: 
            cfl: CFL
            g: 
        """
        self.width = width
        self.B = width  # 
        self.length = length
        self.L = length  # 
        self.n_cells = n_cells
        self.n = manning_n
        self.S0 = slope
        self.cfl = cfl
        self.g = g
        
        #  =  + 2ghost
        self.n_total = n_cells + 2
        
        # 
        self.dx = length / n_cells
        
        # ghost cells
        self.h = np.zeros(self.n_total)
        self.Q = np.zeros(self.n_total)
        
        # 
        self.t = 0.0
        self.dt = 0.0
        self.step_count = 0
        
        # 
        self.initial_mass = 0.0
        
        print(f"EdgeWithGhostCells:")
        print(f"  : {n_cells}")
        print(f"  ghost: {self.n_total}")
        print(f"  dx = {self.dx:.3f} m")
    
    def initialize(self, h_init: float, Q_init: float):
        """
        
        
        Args:
            h_init: 
            Q_init: 
        """
        #  [1] to [n_cells]
        self.h[1:-1] = h_init
        self.Q[1:-1] = Q_init
        
        # ghost cells
        self.h[0] = h_init
        self.Q[0] = Q_init
        self.h[-1] = h_init
        self.Q[-1] = Q_init
        
        # 
        self.initial_mass = np.sum(self.h[1:-1] * self.B * self.dx)
        
        print(f"  : {self.initial_mass:.2f} m³")
    
    def set_left_ghost(self, h: float, Q: float):
        """ghost cell"""
        self.h[0] = h
        self.Q[0] = Q
    
    def set_right_ghost(self, h: float, Q: float):
        """ghost cell"""
        self.h[-1] = h
        self.Q[-1] = Q
    
    def get_left_interior_state(self) -> Tuple[float, float]:
        """"""
        return self.h[1], self.Q[1]
    
    def get_right_interior_state(self) -> Tuple[float, float]:
        """"""
        return self.h[-2], self.Q[-2]
    
    def compute_dt(self) -> float:
        """CFL"""
        # 
        h_interior = self.h[1:-1]
        Q_interior = self.Q[1:-1]
        
        v = Q_interior / (self.B * h_interior + 1e-10)
        c = np.sqrt(self.g * h_interior)
        lambda_max = np.max(np.abs(v) + c)
        
        if lambda_max < 1e-10:
            lambda_max = 1.0
        
        dt = self.cfl * self.dx / lambda_max
        return dt
    
    def hll_flux(self, h_L: float, Q_L: float, h_R: float, Q_R: float) -> np.ndarray:
        """
        HLL Riemann
        
        Args:
            h_L, Q_L: 
            h_R, Q_R: 
        
        Returns:
            F:  [F_h, F_Q]
        """
        # 
        u_L = Q_L / (self.B * h_L + 1e-10)
        u_R = Q_R / (self.B * h_R + 1e-10)
        
        c_L = np.sqrt(self.g * h_L)
        c_R = np.sqrt(self.g * h_R)
        
        # 
        s_L = min(u_L - c_L, u_R - c_R)
        s_R = max(u_L + c_L, u_R + c_R)
        
        # 
        F_L = np.array([Q_L, Q_L * u_L + 0.5 * self.g * self.B * h_L**2])
        F_R = np.array([Q_R, Q_R * u_R + 0.5 * self.g * self.B * h_R**2])
        
        # HLL
        if s_L >= 0:
            return F_L
        elif s_R <= 0:
            return F_R
        else:
            U_L = np.array([self.B * h_L, Q_L])
            U_R = np.array([self.B * h_R, Q_R])
            return (s_R * F_L - s_L * F_R + s_L * s_R * (U_R - U_L)) / (s_R - s_L)
    
    def compute_source(self, i: int) -> np.ndarray:
        """
        
        
        Args:
            i: 
        
        Returns:
            S:  [S_h, S_Q]
        """
        h = self.h[i]
        Q = self.Q[i]
        
        if h < 1e-6:
            return np.array([0.0, 0.0])
        
        # Manning
        v = Q / (self.B * h)
        R_h = h  # 
        S_f = (self.n * abs(v) * v) / (R_h**(4/3))
        
        # 
        S_h = 0.0
        S_Q = self.g * self.B * h * (self.S0 - S_f)
        
        return np.array([S_h, S_Q])
    
    def step(self, dt: Optional[float] = None):
        """
        EulerTVD-RK2
        
        : ghost cells
        
        Args:
            dt: None
        """
        if dt is None:
            dt = self.compute_dt()
        
        self.dt = dt
        
        # Euler
        self._update_interior_euler(dt)
        
        self.t += dt
        self.step_count += 1
    
    def _update_interior_euler(self, dt: float):
        """Euler"""
        # 
        h_old = self.h.copy()
        Q_old = self.Q.copy()
        
        # 
        fluxes_h = []
        fluxes_Q = []
        
        for i in range(self.n_total - 1):
            F = self.hll_flux(h_old[i], Q_old[i], h_old[i+1], Q_old[i+1])
            fluxes_h.append(F[0])
            fluxes_Q.append(F[1])
        
        fluxes_h = np.array(fluxes_h)
        fluxes_Q = np.array(fluxes_Q)
        
        #  [1] to [n_cells]
        for i in range(1, self.n_cells + 1):
            # 
            dF_h = fluxes_h[i] - fluxes_h[i-1]
            dF_Q = fluxes_Q[i] - fluxes_Q[i-1]
            
            # 
            S = self.compute_source(i)
            
            # FVM
            self.h[i] = h_old[i] - dt / self.dx * dF_h + dt * S[0]
            self.Q[i] = Q_old[i] - dt / self.dx * dF_Q + dt * S[1]
            
            # 
            if self.h[i] < 0.001:
                self.h[i] = 0.001
                self.Q[i] = 0.0
    
    def get_mass_error(self) -> float:
        """%"""
        current_mass = np.sum(self.h[1:-1] * self.B * self.dx)
        if self.initial_mass > 1e-10:
            return (current_mass - self.initial_mass) / self.initial_mass * 100.0
        return 0.0
    
    def get_state(self) -> dict:
        """"""
        return {
            't': self.t,
            'step': self.step_count,
            'h': self.h[1:-1].copy(),
            'Q': self.Q[1:-1].copy(),
            'x': np.linspace(self.dx/2, self.length - self.dx/2, self.n_cells),
            'mass_error': self.get_mass_error()
        }


if __name__ == '__main__':
    print("=" * 80)
    print("Ghost Cell")
    print("=" * 80)
    
    # 
    edge = EdgeWithGhostCells(
        width=10.0, length=1000.0, n_cells=50,
        manning_n=0.025, slope=0.001,
        cfl=0.5
    )
    
    # 
    edge.initialize(h_init=2.0, Q_init=50.0)
    
    # ghost cells
    edge.set_left_ghost(h=2.0, Q=50.0)
    edge.set_right_ghost(h=2.0, Q=50.0)
    
    # 
    print("\n500...")
    for i in range(500):
        edge.step()
        
        if (i + 1) % 100 == 0:
            state = edge.get_state()
            print(f"  {i+1:3d}, t={state['t']:6.1f}s, ={state['mass_error']:+.4f}%")
    
    # 
    state = edge.get_state()
    print(f"\n:")
    print(f"  : {state['mass_error']:.4f}%")
    print(f"  : {np.mean(state['h']):.3f}m")
    print(f"  : {np.mean(state['Q']):.3f}m³/s")
    
    if abs(state['mass_error']) < 1.0:
        print("\n Ghost Cell")
    else:
        print("\n[WARN] ")
    
    print("=" * 80)
