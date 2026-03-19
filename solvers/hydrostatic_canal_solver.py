#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


CanalSolver
Preissmann


- Audusse et al. (2004) SIAM 
- CanalSolver

: Claude
: 2025-10-23
"""

import logging
import numpy as np
import math
from typing import List, Tuple, Optional
import sys
import os

logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.hydrostatic_reconstruction_v3 import BoundaryType
from solvers.gate import PumpStation  # PumpStation


class HydrostaticCanalSolver:
    """
    

    
    - 
    - HLL Riemann
    - Preissmann
    - 
    """

    def __init__(self,
                 length: float = 1000.0,
                 nx: int = 201,
                 B: float = 10.0,
                 S0: float = 0.001,
                 n: float = 0.025,
                 g: float = 9.81,
                 internal_structures: list = None,
                 x_grid: np.ndarray = None,
                 bc_left: BoundaryType = BoundaryType.TRANSMISSIVE,
                 bc_right: BoundaryType = BoundaryType.TRANSMISSIVE,
                 theta: float = 0.6,
                 omega: float = 0.95,
                 eps_dry: float = 1e-6,
                 use_muscl: bool = False,
                 muscl_limiter: str = 'minmod',
                 time_integrator: str = 'euler'):
        """
        

        Args:
            length:  (m)
            nx: 
            B:  (m)
            S0:  (floatndarray)
                - float: 
                - ndarray: nx-1
            n: Manning
            g:  (m/s²)
            internal_structures:  [(position, structure_obj), ...]
            x_grid: 
            bc_left: 
            bc_right: 
            theta: Preissmann (0.5-1.0)
            omega:  (0-1)
            eps_dry:  (m)
            use_muscl: MUSCLFalse
            muscl_limiter: MUSCL ('minmod', 'van_leer', 'superbee')
            time_integrator:  ('euler', 'rk2', 'rk3')
        """
        self.length = length
        self.B = B
        self.n = n
        self.g = g

        # 
        # S0floatndarray
        self.theta = theta
        self.omega = omega
        self.eps_dry = eps_dry
        self.bc_left = bc_left
        self.bc_right = bc_right
        self.use_muscl = use_muscl
        self.muscl_limiter = muscl_limiter
        self.time_integrator = time_integrator
        
        # v7.0 
        # HEC-RASMIKE 11

        # 
        if x_grid is not None:
            self.x = x_grid
            self.nx = len(x_grid)
            self.is_uniform_grid = False
            self.dx_local = np.diff(x_grid)
            self.dx = np.mean(self.dx_local)
        else:
            self.nx = nx
            self.dx = length / (nx - 1)
            self.x = np.linspace(0, length, nx)
            self.is_uniform_grid = True
            self.dx_local = np.ones(nx-1) * self.dx

        # S0
        if isinstance(S0, (int, float)):
            # uniform
            self.S0 = np.ones(self.nx - 1) * float(S0)
            self.is_uniform_slope = True
            self.S0_scalar = float(S0)  # 
        else:
            # 
            S0_array = np.asarray(S0, dtype=float)
            if len(S0_array) != self.nx - 1:
                raise ValueError(f"S0({len(S0_array)})nx-1({self.nx-1})")
            self.S0 = S0_array
            self.is_uniform_slope = False
            self.S0_scalar = np.mean(S0_array)  # 

        # 
        self.z = self._compute_bed_elevation()

        # 
        self.h = np.ones(nx) * 1.0  #  (m)
        self.hu = np.ones(nx) * 5.0  #  hu (m²/s)

        # 
        self.internal_structures = internal_structures or []
        self._setup_internal_structures()

        # 
        self.h_history = []
        self.Q_history = []
        self.t_history = []

        # 
        self.current_time = 0.0

    def compute_dt(self, cfl: float = 0.9) -> float:
        """
        Compute stable time step based on CFL condition
        
        Args:
            cfl: CFL number (default 0.9)
            
        Returns:
            dt: Stable time step (s)
        """
        h = self.h
        # Avoid division by zero
        mask = h > self.eps_dry
        u = np.zeros_like(h)
        u[mask] = self.hu[mask] / h[mask]
        
        c = np.sqrt(self.g * h)
        wave_speed = np.abs(u) + c
        max_speed = np.max(wave_speed)
        
        if max_speed < 1e-6:
            return 1.0  # Default large step if fluid is at rest
            
        return cfl * self.dx / max_speed

    def step(self, dt: float):
        """
        Perform one time step integration
        
        Args:
            dt: Time step (s)
        """
        # 1. Compute fluxes and sources
        F_mass, F_mom, S_mass, S_mom = self.compute_fluxes_and_sources(
            self.h, self.hu, self.z, self.dx
        )
        
        # 2. Update conserved variables
        # dU/dt + dF/dx = S
        # U_new = U_old - dt/dx * (F_R - F_L) + dt * S
        
        # Mass conservation
        # F_mass has size n_cells + 1 (interfaces)
        # Flux difference for cell i is F[i+1] - F[i]
        flux_diff_mass = F_mass[1:] - F_mass[:-1]
        self.h -= (dt / self.dx) * flux_diff_mass
        self.h += dt * S_mass
        
        # Momentum conservation
        flux_diff_mom = F_mom[1:] - F_mom[:-1]
        self.hu -= (dt / self.dx) * flux_diff_mom
        self.hu += dt * S_mom
        
        # 3. Apply internal boundary conditions (structures)
        self._apply_internal_bc(self.current_time, None)
        
        # 4. Handle dry cells and physical constraints
        self.h = np.maximum(self.h, self.eps_dry)
        # Zero velocity in dry cells
        dry_mask = self.h <= self.eps_dry
        self.hu[dry_mask] = 0.0
        
        # 5. Update time
        self.current_time += dt

    def _compute_bed_elevation(self) -> np.ndarray:
        """
        

        Returns:
            z:  [nx]
        """
        z = np.zeros(self.nx)
        z[0] = 0.0  # 0

        # 
        for i in range(self.nx - 1):
            # z[i+1] = z[i] - S0[i] * dx[i]
            # S0
            z[i + 1] = z[i] - self.S0[i] * self.dx_local[i]

        return z

    def _setup_internal_structures(self):
        """Setup internal structures by finding nearest interface indices"""
        self.structure_indices = []
        self.structure_objects = []

        for position, structure in self.internal_structures:
            # Find nearest interface
            # x has size nx (cell centers/nodes). Interfaces are at i+1/2?
            # In this solver, x seems to be nodes.
            # F_mass has size nx+1.
            # Let's assume structure is at interface i if x[i-1] < pos < x[i]
            # or simply nearest node.
            
            # Let's find the nearest node index, and treat it as the interface to the right of that node?
            # Or better, find the index i such that the structure is between x[i] and x[i+1].
            # Then we modify flux at interface i+1 (which connects cell i and i+1).
            
            # F_mass[i] is flux at interface i-1/2? No.
            # F_mass has size nx+1.
            # F[0] is left boundary. F[nx] is right boundary.
            # F[i] is flux between cell i-1 and i.
            
            # Find i such that x[i-1] <= pos <= x[i]
            # If pos is 500, and x is 0, 10, ..., 1000.
            # 500 is at index 50.
            # We want to modify flux at interface 50?
            
            idx = np.searchsorted(self.x, position)
            # idx is such that x[idx-1] <= pos < x[idx]
            # So structure is between cell idx-1 and idx.
            # The flux between them is F[idx].
            
            if 0 < idx < self.nx:
                self.structure_indices.append(idx)
                self.structure_objects.append(structure)

    def reconstruct_interface(
        self, h_L: float, z_L: float, h_R: float, z_R: float
    ) -> Tuple[float, float]:
        """
        

        Args:
            h_L, z_L: 
            h_R, z_R: 

        Returns:
            (h_star_L, h_star_R): 
        """
        eta_L = h_L + z_L
        eta_R = h_R + z_R
        z_interface = max(z_L, z_R)

        h_star_L = max(0.0, eta_L - z_interface)
        h_star_R = max(0.0, eta_R - z_interface)

        return h_star_L, h_star_R

    def hll_flux(
        self, h_L: float, hu_L: float, h_R: float, hu_R: float
    ) -> Tuple[float, float]:
        """
        HLL RiemannHLLC

        Args:
            h_L, hu_L: 
            h_R, hu_R: 

        Returns:
            (F_mass, F_momentum): 
        """
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        # Clamp inputs to prevent overflow
        h_max_safe = 1e8
        h_L = min(max(h_L, 0.0), h_max_safe)
        h_R = min(max(h_R, 0.0), h_max_safe)
        hu_max_safe = 1e10
        hu_L = max(-hu_max_safe, min(hu_max_safe, hu_L))
        hu_R = max(-hu_max_safe, min(hu_max_safe, hu_R))

        u_L = hu_L / h_L if h_L > self.eps_dry else 0.0
        u_R = hu_R / h_R if h_R > self.eps_dry else 0.0
        u_max = 100.0
        u_L = max(-u_max, min(u_max, u_L))
        u_R = max(-u_max, min(u_max, u_R))

        c_L = math.sqrt(self.g * h_L) if h_L > self.eps_dry else 0.0
        c_R = math.sqrt(self.g * h_R) if h_R > self.eps_dry else 0.0

        s_L = min(u_L - c_L, u_R - c_R)
        s_R = max(u_L + c_L, u_R + c_R)

        if abs(s_L) < 1e-14 and abs(s_R) < 1e-14:
            s_L = -1e-10
            s_R = 1e-10

        #
        if h_L > self.eps_dry:
            F_mass_L = hu_L
            h_L_c = min(h_L, 1e6)  # Prevent h**2 overflow
            F_mom_L = hu_L * u_L + 0.5 * self.g * h_L_c**2
        else:
            F_mass_L = 0.0
            F_mom_L = 0.0

        if h_R > self.eps_dry:
            F_mass_R = hu_R
            h_R_c = min(h_R, 1e6)  # Prevent h**2 overflow
            F_mom_R = hu_R * u_R + 0.5 * self.g * h_R_c**2
        else:
            F_mass_R = 0.0
            F_mom_R = 0.0

        # HLL
        if s_L >= 0:
            return F_mass_L, F_mom_L
        elif s_R <= 0:
            return F_mass_R, F_mom_R
        else:
            U_L = [h_L, hu_L]
            U_R = [h_R, hu_R]
            F_L = [F_mass_L, F_mom_L]
            F_R = [F_mass_R, F_mom_R]

            F_mass_HLL = (s_R * F_L[0] - s_L * F_R[0] +
                         s_L * s_R * (U_R[0] - U_L[0])) / (s_R - s_L)
            F_mom_HLL = (s_R * F_L[1] - s_L * F_R[1] +
                        s_L * s_R * (U_R[1] - U_L[1])) / (s_R - s_L)

            return F_mass_HLL, F_mom_HLL

    def minmod(self, a: float, b: float) -> float:
        """
        Minmod slope limiter
        
        TVD
        """
        if a * b <= 0:
            return 0.0
        elif abs(a) < abs(b):
            return a
        else:
            return b
    
    def van_leer(self, a: float, b: float) -> float:
        """
        Van Leer slope limiter
        
        
        """
        if a * b <= 0:
            return 0.0
        else:
            return 2.0 * a * b / (a + b)
    
    def superbee(self, a: float, b: float) -> float:
        """
        Superbee slope limiter
        
        
        """
        if a * b <= 0:
            return 0.0
        elif abs(a) > abs(b):
            s1 = self.minmod(a, 2.0 * b)
        else:
            s1 = self.minmod(2.0 * a, b)
        return s1
    
    def muscl_reconstruct(
        self, 
        U_minus: float, 
        U_center: float, 
        U_plus: float,
        limiter: str = 'minmod'
    ) -> Tuple[float, float]:
        """
        MUSCL
        
        
        
        Args:
            U_minus: 
            U_center: 
            U_plus: 
            limiter:  ('minmod', 'van_leer', 'superbee')
        
        Returns:
            U_L: 
            U_R: 
        """
        # 
        delta_minus = U_center - U_minus
        delta_plus = U_plus - U_center
        
        # 
        if limiter == 'minmod':
            slope = self.minmod(delta_minus, delta_plus)
        elif limiter == 'van_leer':
            slope = self.van_leer(delta_minus, delta_plus)
        elif limiter == 'superbee':
            slope = self.superbee(delta_minus, delta_plus)
        else:
            slope = self.minmod(delta_minus, delta_plus)  # minmod
        
        # 
        U_L = U_center - 0.5 * slope  # 
        U_R = U_center + 0.5 * slope  # 
        
        return U_L, U_R

    def hllc_flux(
        self, h_L: float, hu_L: float, h_R: float, hu_R: float
    ) -> Tuple[float, float]:
        """
        HLLC Riemann
        
        HLLCHLL
        - contact discontinuity
        - 
        - 
        
        
        - Toro, E.F. (2009) "Riemann Solvers and Numerical Methods for Fluid Dynamics"
        - Shallow Water Equations

        Args:
            h_L, hu_L: 
            h_R, hu_R: 

        Returns:
            (F_mass, F_momentum): 
        """
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        # Clamp inputs to prevent overflow in all downstream computations
        h_max_safe = 1e8  # Max physically meaningful depth
        h_L = min(max(h_L, 0.0), h_max_safe)
        h_R = min(max(h_R, 0.0), h_max_safe)
        hu_max_safe = 1e10
        hu_L = max(-hu_max_safe, min(hu_max_safe, hu_L))
        hu_R = max(-hu_max_safe, min(hu_max_safe, hu_R))

        u_L = hu_L / h_L if h_L > self.eps_dry else 0.0
        u_R = hu_R / h_R if h_R > self.eps_dry else 0.0

        # Clamp velocities
        u_max = 100.0
        u_L = max(-u_max, min(u_max, u_L))
        u_R = max(-u_max, min(u_max, u_R))

        c_L = math.sqrt(self.g * h_L) if h_L > self.eps_dry else 0.0
        c_R = math.sqrt(self.g * h_R) if h_R > self.eps_dry else 0.0

        # Roe averages - Toro (2009), Section 10.5
        h_avg = 0.5 * (h_L + h_R)
        c_avg = math.sqrt(self.g * h_avg) if h_avg > self.eps_dry else 0.0

        if h_L + h_R > self.eps_dry:
            sqrt_hL = math.sqrt(h_L) if h_L > 0 else 0.0
            sqrt_hR = math.sqrt(h_R) if h_R > 0 else 0.0
            denom = sqrt_hL + sqrt_hR
            u_avg = (u_L * sqrt_hL + u_R * sqrt_hR) / denom if denom > 1e-14 else 0.0
        else:
            u_avg = 0.0

        s_L = min(u_L - c_L, u_avg - c_avg)
        s_R = max(u_R + c_R, u_avg + c_avg)

        # 
        if abs(s_L) < 1e-14 and abs(s_R) < 1e-14:
            s_L = -1e-10
            s_R = 1e-10

        #
        if h_L > self.eps_dry:
            F_mass_L = hu_L
            h_L_c = min(h_L, 1e6)  # Prevent h**2 overflow
            F_mom_L = hu_L * u_L + 0.5 * self.g * h_L_c**2
        else:
            F_mass_L = 0.0
            F_mom_L = 0.0

        if h_R > self.eps_dry:
            F_mass_R = hu_R
            h_R_c = min(h_R, 1e6)  # Prevent h**2 overflow
            F_mom_R = hu_R * u_R + 0.5 * self.g * h_R_c**2
        else:
            F_mass_R = 0.0
            F_mom_R = 0.0

        # HLLC
        if s_L >= 0:
            # 
            return F_mass_L, F_mom_L
        elif s_R <= 0:
            # 
            return F_mass_R, F_mom_R
        else:
            # s_star
            
            # contact wave speed
            # Rankine-Hugoniot with overflow protection
            denom_star = s_R * h_R - s_L * h_L
            if abs(s_R - s_L) > 1e-14 and abs(denom_star) > 1e-14:
                s_star = (s_R * hu_R - s_L * hu_L + F_mom_L - F_mom_R) / denom_star
                if not math.isfinite(s_star):
                    s_star = 0.5 * (u_L + u_R)
            else:
                s_star = 0.5 * (u_L + u_R)

            if s_star >= 0:
                # s_L < 0 < s_star
                if abs(s_L - s_star) > 1e-14:
                    h_star_L = h_L * (s_L - u_L) / (s_L - s_star)
                    if not math.isfinite(h_star_L) or h_star_L < 0:
                        h_star_L = h_L
                    hu_star_L = h_star_L * s_star
                else:
                    h_star_L = h_L
                    hu_star_L = hu_L

                F_mass_star = F_mass_L + s_L * (h_star_L - h_L)
                F_mom_star = F_mom_L + s_L * (hu_star_L - hu_L)

                return F_mass_star, F_mom_star
            else:
                # s_star < 0 < s_R
                if abs(s_R - s_star) > 1e-14:
                    h_star_R = h_R * (s_R - u_R) / (s_R - s_star)
                    if not math.isfinite(h_star_R) or h_star_R < 0:
                        h_star_R = h_R
                    hu_star_R = h_star_R * s_star
                else:
                    h_star_R = h_R
                    hu_star_R = hu_R

                F_mass_star = F_mass_R + s_R * (h_star_R - h_R)
                F_mom_star = F_mom_R + s_R * (hu_star_R - hu_R)
                
                return F_mass_star, F_mom_star

    def setup_ghost_cells(
        self, h: np.ndarray, hu: np.ndarray, z: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        

        Args:
            h, hu, z: 

        Returns:
            h_ext, hu_ext, z_ext: 
        """
        n_cells = len(h)

        h_ext = np.zeros(n_cells + 2)
        hu_ext = np.zeros(n_cells + 2)
        z_ext = np.zeros(n_cells + 2)

        # 
        h_ext[1:-1] = h
        hu_ext[1:-1] = hu
        z_ext[1:-1] = z

        # 
        if self.bc_left == BoundaryType.TRANSMISSIVE:
            eta_0 = h[0] + z[0]
            z_ext[0] = z[0]
            h_ext[0] = eta_0 - z_ext[0]
            hu_ext[0] = hu[0]
        elif self.bc_left == BoundaryType.REFLECTIVE:
            h_ext[0] = h[0]
            hu_ext[0] = -hu[0]
            z_ext[0] = z[0]
        elif self.bc_left == BoundaryType.EXTRAPOLATION:
            h_ext[0] = h[0]
            hu_ext[0] = hu[0]
            z_ext[0] = z[0]

        # 
        if self.bc_right == BoundaryType.TRANSMISSIVE:
            eta_n = h[-1] + z[-1]
            z_ext[-1] = z[-1]
            h_ext[-1] = eta_n - z_ext[-1]
            hu_ext[-1] = hu[-1]
        elif self.bc_right == BoundaryType.REFLECTIVE:
            h_ext[-1] = h[-1]
            hu_ext[-1] = -hu[-1]
            z_ext[-1] = z[-1]
        elif self.bc_right == BoundaryType.EXTRAPOLATION:
            h_ext[-1] = h[-1]
            hu_ext[-1] = hu[-1]
            z_ext[-1] = z[-1]

        return h_ext, hu_ext, z_ext

    def compute_fluxes_and_sources(
        self, h: np.ndarray, hu: np.ndarray, z: np.ndarray, dx: float,
        include_pump_source: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        

        Args:
            h:  [n_cells]
            hu:  [n_cells]
            z:  [n_cells]
            dx: 

        Returns:
            (F_mass, F_momentum, S_mass, S_momentum)
        """
        n_cells = len(h)

        # 
        h_ext, hu_ext, z_ext = self.setup_ghost_cells(h, hu, z)

        # 
        F_mass = np.zeros(n_cells + 1)
        F_momentum = np.zeros(n_cells + 1)

        # 
        h_star_interfaces = np.zeros((n_cells + 1, 2))

        # 
        for i in range(n_cells + 1):
            # ========== MUSCL ==========
            if self.use_muscl and i >= 1 and i < n_cells:
                # MUSCLeta=h+z
                # 
                
                # 
                eta_ext = h_ext + z_ext
                
                # i
                _, eta_L_from_i = self.muscl_reconstruct(
                    eta_ext[i-1], eta_ext[i], eta_ext[i+1], self.muscl_limiter
                )
                
                # i+1
                eta_R_from_i1, _ = self.muscl_reconstruct(
                    eta_ext[i], eta_ext[i+1], eta_ext[i+2], self.muscl_limiter
                )
                
                # etah
                z_L = z_ext[i]
                z_R = z_ext[i+1]
                h_L = max(eta_L_from_i - z_L, self.eps_dry)
                h_R = max(eta_R_from_i1 - z_R, self.eps_dry)
                
                # huMUSCL
                _, hu_L_from_i = self.muscl_reconstruct(
                    hu_ext[i-1], hu_ext[i], hu_ext[i+1], self.muscl_limiter
                )
                hu_R_from_i1, _ = self.muscl_reconstruct(
                    hu_ext[i], hu_ext[i+1], hu_ext[i+2], self.muscl_limiter
                )
                
                hu_L = hu_L_from_i
                hu_R = hu_R_from_i1
            else:
                # 
                h_L = h_ext[i]
                hu_L = hu_ext[i]
                z_L = z_ext[i]

                h_R = h_ext[i+1]
                hu_R = hu_ext[i+1]
                z_R = z_ext[i+1]

            # 
            h_star_L, h_star_R = self.reconstruct_interface(h_L, z_L, h_R, z_R)
            h_star_interfaces[i, 0] = h_star_L
            h_star_interfaces[i, 1] = h_star_R

            # 
            if h_L > self.eps_dry:
                hu_star_L = hu_L * (h_star_L / h_L)
            else:
                hu_star_L = 0.0

            if h_R > self.eps_dry:
                hu_star_R = hu_R * (h_star_R / h_R)
            else:
                hu_star_R = 0.0

            # HLLCHLL
            F_mass[i], F_momentum[i] = self.hllc_flux(
                h_star_L, hu_star_L, h_star_R, hu_star_R
            )

        # 
        S_mass = np.zeros(n_cells)
        S_momentum = np.zeros(n_cells)

        for i in range(n_cells):
            # 
            h_star_L = h_star_interfaces[i, 1]
            # 
            h_star_R = h_star_interfaces[i+1, 0]

            # Audusse - with overflow protection
            h_sL = min(h_star_L, 1e6)  # Cap to prevent h**2 overflow
            h_sR = min(h_star_R, 1e6)
            S_gravity = 0.5 * self.g * (h_sR**2 - h_sL**2) / dx

            #
            if h[i] > self.eps_dry and abs(self.n) > 1e-10:
                u_i = hu[i] / h[i]
                u_i = max(-100.0, min(100.0, u_i))  # Clamp velocity
                R_i = max(h[i], 1e-8)  # Ensure R > 0 for power operation
                S_friction = -self.g * self.n**2 * abs(u_i) * hu[i] / (R_i**(4/3))
                S_friction = max(-1e6, min(1e6, S_friction))  # Cap friction source
            else:
                S_friction = 0.0

            S_mass[i] = 0.0
            S_momentum[i] = S_gravity + S_friction

        # ========================================================================
        # v5.2 - 
        # ========================================================================
        # 
        # 
        # 
        #   S_momentum = ρ * g * H_pump * Q / Δx
        # 
        # 
        #   H_pump:  (m)
        #   Q:  (m³/s)
        #   Δx:  (m)
        #
        # 
        #   [OK] 
        #   [OK] 
        #   [OK] 
        #
        # v7.0: 
        # ========================================================================

        # ========================================================================
        # Internal Structures Coupling (Flux Overwrite)
        # ========================================================================
        if hasattr(self, 'structure_indices') and self.structure_indices:
            for idx, structure in zip(self.structure_indices, self.structure_objects):
                if idx >= len(F_mass): continue
                
                # Get upstream and downstream states
                # Interface idx connects cell idx-1 and idx
                h_up = h[idx-1]
                h_down = h[idx]
                
                # Calculate discharge
                try:
                    # Try new interface first
                    if hasattr(structure, 'compute_discharge'):
                        Q_struc, _ = structure.compute_discharge(h_up, h_down)
                    elif hasattr(structure, 'calculate_discharge'):
                        Q_struc, _ = structure.calculate_discharge(h_up, h_down)
                    else:
                        continue
                        
                    # Overwrite Mass Flux
                    F_mass[idx] = float(Q_struc)
                    
                    # Debug print every 100 steps or so (how to know step? just print if t > 0)
                    # Or just print if Q_struc is unexpected
                    # print(f"Struc {idx}: h_up={h_up:.2f}, h_dn={h_down:.2f}, Q={Q_struc:.2f}")
                    
                    # Overwrite Momentum Flux
                    # F_mom = Q * v + g*h^2/2
                    # Approximate v = Q / (h * B)
                    # Use upstream side for momentum flux? Or average?
                    # Simple approximation:
                    if h_up > self.eps_dry:
                        v_up = Q_struc / (h_up * self.B)
                        F_momentum[idx] = Q_struc * v_up + 0.5 * self.g * h_up**2
                    else:
                        F_momentum[idx] = 0.0
                        
                except Exception as e:
                    logger.warning(f"Structure discharge calculation failed at index {idx}: {e}")

        return F_mass, F_momentum, S_mass, S_momentum

    def _apply_internal_bc(self, t: float = 0.0, Q_target: float = None,
                          max_iter: int = 20, tol: float = 0.01, relax: float = 0.5):
        """
        

        
        : Q = f(h_up, h_down)
        Q_targeth_upf(h_up, h_down) = Q_target

        

        Args:
            t:  (s)
            Q_target:  (m³/s)
            max_iter: 
            tol:  (m³/s)
            relax: 
        """
        if not self.structure_indices or Q_target is None:
            return

        for iter_count in range(max_iter):
            converged = True

            for idx, structure in zip(self.structure_indices, self.structure_objects):
                # PumpStation
                from solvers.gate import PumpStation

                # 
                structure.update_time(t)

                # 
                if idx <= 0 or idx >= self.nx - 1:
                    continue

                #  v7.0
                if isinstance(structure, PumpStation):
                    # 
                    h_up = self.h[idx - 1]
                    hu_up = self.hu[idx - 1]
                    z_up = self.z[idx - 1]
                    z_down = self.z[idx + 1]
                    
                    # h_down = h_up + (z_up - z_down) + H_pump
                    H_pump = structure.rated_head
                    h_down = h_up + (z_up - z_down) + H_pump
                    h_down = max(h_down, self.eps_dry)
                    
                    # 
                    self.h[idx + 1] = h_down
                    self.hu[idx + 1] = hu_up  # 
                    self.h[idx] = (h_up + h_down) / 2.0  # 
                    self.hu[idx] = hu_up
                    
                    continue  # 

                # idxidx-1idx+1
                h_up = self.h[idx - 1]
                h_down = self.h[idx + 1]

                # 
                Q_gate_current, _ = structure.calculate_discharge(h_up, h_down, t)

                # 
                residual = Q_target - Q_gate_current

                if abs(residual) > tol:
                    converged = False

                    # 
                    # Q = f(h_up, h_down)f(h_up, h_down) = Q_target
                    # Δh_up ≈ (Q_target - Q_current) / (dQ/dh_up)
                    dQ_dh_up, dQ_dh_down = structure.calculate_discharge_derivatives(h_up, h_down, t)

                    if abs(dQ_dh_up) > 1e-6:
                        # 
                        dh_up = residual / dQ_dh_up
                        # 
                        dh_up = np.clip(dh_up, -0.1, 0.1)
                        # 
                        self.h[idx - 1] = h_up + relax * dh_up
                        # 
                        self.h[idx - 1] = max(self.eps_dry, self.h[idx - 1])

            if converged:
                break

        # 
        # _apply_pump_head_jump

    def _get_pump_region_mask(self) -> np.ndarray:
        """
        
        
        3
        
        
        Returns:
            mask: True
        """
        mask = np.zeros(self.nx, dtype=bool)

        if not self.structure_indices or not self.structure_objects:
            return mask

        for idx, structure in zip(self.structure_indices, self.structure_objects):
            from solvers.gate import PumpStation

            if not isinstance(structure, PumpStation) or not structure.is_running:
                continue

            # 
            if idx <= 0 or idx >= self.nx - 1:
                continue

            # 3
            mask[idx - 1] = True
            mask[idx] = True
            mask[idx + 1] = True

        return mask

    
    def _apply_pump_internal_bc(self, conserve_local_flow=False):
        """
        v7.0 - 
        
        HEC-RASMIKE 11
        =========================================
        
        
        
            E_up + H_pump = E_down
            (z_up + h_up + V²/2g) + H_pump = (z_down + h_down + V²/2g)
        
        
            z_up + h_up + H_pump = z_down + h_down
            → h_down = h_up + (z_up - z_down) + H_pump
        
        
        ----------
        A: z_down ≈ z_up
            → h_down ≈ h_up + H_pump
        
        B: z_down = z_up + Δz
            → h_down = h_up + H_pump - Δz
            →  Δz ≈ H_pump h_down ≈ h_up
        
        
        --------
        [OK]  z 
        [OK] 
        [OK] /
        [OK] HEC-RASMIKE 11SWMM
        
        
        ------
        conserve_local_flow: bool
            False
            True
        """
        if not self.structure_indices or not self.structure_objects:
            return
        
        from solvers.gate import PumpStation
        
        for idx, structure in zip(self.structure_indices, self.structure_objects):
            if not isinstance(structure, PumpStation):
                continue
            
            # 
            if idx <= 0 or idx >= self.nx - 1:
                continue
            
            # =====================================================================
            # 1. 
            # =====================================================================
            h_up = self.h[idx - 1]  # 
            hu_up = self.hu[idx - 1]  # 
            z_up = self.z[idx - 1]  # 
            
            # =====================================================================
            # 2. 
            # =====================================================================
            z_down = self.z[idx + 1]  # 
            
            # =====================================================================
            # 3. 
            # =====================================================================
            # z_up + h_up + H_pump = z_down + h_down
            # h_down = h_up + (z_up - z_down) + H_pump
            H_pump = structure.rated_head  # 
            h_down = h_up + (z_up - z_down) + H_pump
            
            # 
            h_down = max(h_down, self.eps_dry)
            
            # =====================================================================
            # 4. 
            # =====================================================================
            # Q_down = Q_up
            hu_down = hu_up
            
            # 
            self.h[idx + 1] = h_down
            self.hu[idx + 1] = hu_down
            
            # =====================================================================
            # 5. 
            # =====================================================================
            # 
            self.h[idx] = (h_up + h_down) / 2.0
            # 
            self.hu[idx] = hu_up
    
    def _apply_pump_region_constraints(self):
        """
         v3.0
        
        15
        - Preissmann PDE
        - ""
        - 
        - ""
        
        (_apply_pump_internal_bc)
        
        """
        # 
        self._apply_pump_internal_bc()


    def _apply_pump_head_jump(self):
        """
        
        
        _apply_pump_internal_bc
        
        """
        self._apply_pump_internal_bc(conserve_local_flow=False)

    def _compute_time_derivative(
        self, h: np.ndarray, hu: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
         dU/dt
        
         dU/dt = -dF/dx + S
        
        Args:
            h: 
            hu: 
        
        Returns:
            (dhdt, dhudt): 
        """
        # 
        F_mass, F_momentum, S_mass, S_momentum = \
            self.compute_fluxes_and_sources(h, hu, self.z, self.dx)
        
        dhdt = np.zeros(self.nx)
        dhudt = np.zeros(self.nx)
        
        for i in range(self.nx):
            # : dh/dt = -dF_mass/dx + S_mass
            dhdt[i] = -(F_mass[i+1] - F_mass[i])/self.dx + S_mass[i]
            
            # : d(hu)/dt = -dF_momentum/dx + S_momentum
            dhudt[i] = -(F_momentum[i+1] - F_momentum[i])/self.dx + S_momentum[i]
        
        return dhdt, dhudt

    def step_explicit(self, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Euler, RK2, RK3

        Args:
            dt:  (s)

        Returns:
            (h_new, hu_new): 
        """
        if self.time_integrator == 'euler':
            # Euler
            dhdt, dhudt = self._compute_time_derivative(self.h, self.hu)
            h_new = self.h + dt * dhdt
            hu_new = self.hu + dt * dhudt
            
        elif self.time_integrator == 'rk2':
            # Runge-Kutta (Heun's method / RK2)
            # k1 = f(u_n)
            k1_h, k1_hu = self._compute_time_derivative(self.h, self.hu)
            
            # : u_mid = u_n + dt*k1
            h_mid = self.h + dt * k1_h
            hu_mid = self.hu + dt * k1_hu
            
            # k2 = f(u_mid)
            k2_h, k2_hu = self._compute_time_derivative(h_mid, hu_mid)
            
            # u_{n+1} = u_n + dt/2 * (k1 + k2)
            h_new = self.h + 0.5 * dt * (k1_h + k2_h)
            hu_new = self.hu + 0.5 * dt * (k1_hu + k2_hu)
            
        elif self.time_integrator == 'rk3':
            # Runge-Kutta (TVD RK3 / SSP-RK3)
            # k1 = f(u_n)
            k1_h, k1_hu = self._compute_time_derivative(self.h, self.hu)
            
            # : u^(1) = u_n + dt*k1
            h1 = self.h + dt * k1_h
            hu1 = self.hu + dt * k1_hu
            
            # k2 = f(u^(1))
            k2_h, k2_hu = self._compute_time_derivative(h1, hu1)
            
            # : u^(2) = 3/4*u_n + 1/4*(u^(1) + dt*k2)
            h2 = 0.75 * self.h + 0.25 * (h1 + dt * k2_h)
            hu2 = 0.75 * self.hu + 0.25 * (hu1 + dt * k2_hu)
            
            # k3 = f(u^(2))
            k3_h, k3_hu = self._compute_time_derivative(h2, hu2)
            
            # : u_{n+1} = 1/3*u_n + 2/3*(u^(2) + dt*k3)
            h_new = (1.0/3.0) * self.h + (2.0/3.0) * (h2 + dt * k3_h)
            hu_new = (1.0/3.0) * self.hu + (2.0/3.0) * (hu2 + dt * k3_hu)
        else:
            raise ValueError(f"Unknown time_integrator: {self.time_integrator}")

        # 
        self.h[:] = h_new
        self.hu[:] = hu_new
        self._apply_pump_region_constraints()

        return self.h.copy(), self.hu.copy()

    def set_boundary_conditions(
        self,
        Q_in: Optional[float] = None,
        h_out: Optional[float] = None
    ):
        """
        

        Args:
            Q_in:  (m³/s)None
            h_out:  (m)None
        """
        if Q_in is not None:
            self.hu[0] = Q_in / self.B

        if h_out is not None:
            self.h[-1] = h_out

    def step_preissmann(self, dt: float, max_iter: int = 10,
                       enforce_bc: bool = False,
                       Q_in: float = None, h_out: float = None,
                       use_pump_mask: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preissmann

         + Preissmann

        Args:
            dt:  (s)
            max_iter: 
            enforce_bc: 
            Q_in:  (m³/s)enforce_bc=True
            h_out:  (m)enforce_bc=True

        Returns:
            (h_new, hu_new): 
        """
        # 
        h_new = self.h.copy()
        hu_new = self.hu.copy()

        # 
        for iter in range(max_iter):
            #  n+1 
            F_mass_new, F_momentum_new, S_mass_new, S_momentum_new = \
                self.compute_fluxes_and_sources(h_new, hu_new, self.z, self.dx)

            #  n 
            F_mass_old, F_momentum_old, S_mass_old, S_momentum_old = \
                self.compute_fluxes_and_sources(self.h, self.hu, self.z, self.dx)

            # Preissmann
            F_mass = self.theta * F_mass_new + (1 - self.theta) * F_mass_old
            F_momentum = self.theta * F_momentum_new + (1 - self.theta) * F_momentum_old
            S_mass = self.theta * S_mass_new + (1 - self.theta) * S_mass_old
            S_momentum = self.theta * S_momentum_new + (1 - self.theta) * S_momentum_old

            # 
            h_old_iter = h_new.copy()
            hu_old_iter = hu_new.copy()

            # 
            # 
            if use_pump_mask:
                pump_mask = self._get_pump_region_mask()
            else:
                pump_mask = np.zeros(self.nx, dtype=bool)

            # 
            for i in range(self.nx):
                if pump_mask[i]:
                    # 
                    continue
                
                # Update with overflow-safe flux difference
                dF_mass = F_mass[i+1] - F_mass[i]
                dF_mom = F_momentum[i+1] - F_momentum[i]
                if not math.isfinite(dF_mass):
                    dF_mass = 0.0
                if not math.isfinite(dF_mom):
                    dF_mom = 0.0
                dh = dt * (-dF_mass / self.dx + S_mass[i])
                h_new[i] = self.h[i] + dh

                dhu = dt * (-dF_mom / self.dx + S_momentum[i])
                hu_new[i] = self.hu[i] + dhu

            #
            for i in range(self.nx):
                if not pump_mask[i]:
                    h_new[i] = self.omega * h_new[i] + (1 - self.omega) * h_old_iter[i]
                    hu_new[i] = self.omega * hu_new[i] + (1 - self.omega) * hu_old_iter[i]

            # Positivity enforcement and NaN guard
            h_new = np.where(np.isfinite(h_new), h_new, self.h)
            hu_new = np.where(np.isfinite(hu_new), hu_new, self.hu)
            h_new = np.maximum(h_new, 0.0)
            hu_new[h_new < self.eps_dry] = 0.0

            # 
            # [WARN] use_pump_mask=True
            # use_pump_mask=False
            if use_pump_mask:
                self.h[:] = h_new
                self.hu[:] = hu_new
                self._apply_pump_region_constraints()
                h_new = self.h.copy()
                hu_new = self.hu.copy()

            #  
            # 
            if enforce_bc:
                # 
                pump_mask[0] = False
                pump_mask[-1] = False
                
                # 
                if Q_in is not None:
                    hu_new[0] = Q_in / self.B
                
                # 
                if h_out is not None:
                    h_new[-1] = h_out

        return h_new, hu_new

    def solve_steady_state(
        self,
        Q_target: float,
        h_downstream: float,
        max_iterations: int = 5000,
        convergence_tol: float = 0.001,
        dt: float = 0.5,
        verbose: bool = True,
        h_upstream_guess: Optional[float] = None
    ) -> dict:
        """
        

        Args:
            Q_target:  (m³/s)
            h_downstream:  (m)
            max_iterations: 
            convergence_tol: 
            dt:  (s)
            verbose: 
            h_upstream_guess: 

        Returns:
            result: 
        """
        # 
        self.hu = np.ones(self.nx) * Q_target / self.B

        # 
        if h_upstream_guess is None:
            #  
            has_structures = len(self.structure_indices) > 0 if self.structure_indices else False
            
            if has_structures:
                # /20%
                h_upstream_guess = h_downstream * 1.2
            else:
                # 
                # Manning
                from utils.canal_utils import compute_steady_uniform_flow
                try:
                    # 
                    h_uniform = compute_steady_uniform_flow(Q_target, self.B, self.S0_scalar, self.n, self.g)
                    h_upstream_guess = h_uniform
                except Exception as e:
                    logger.warning(f"Steady uniform flow computation failed, using h_downstream as fallback: {e}")
                    h_upstream_guess = h_downstream

        # 
        self.h = np.linspace(h_upstream_guess, h_downstream, self.nx)

        # 
        self.h[-1] = h_downstream

        has_structures = bool(self.structure_indices)
        uniform_target_profile = (
            not has_structures and
            h_upstream_guess is not None and
            abs(h_upstream_guess - h_downstream) <= max(1e-6, 1e-3 * max(abs(h_downstream), 1.0))
        )

        if verbose:
            print(f"")
            print(f"  {Q_target:.3f} m³/s")
            print(f"  {h_downstream:.3f} m")
            print(f"  {h_upstream_guess:.3f} m")
        # 
        for iteration in range(max_iterations):
            h_old = self.h.copy()
            hu_old = self.hu.copy()

            # Enforce the physical steady-state boundary condition directly:
            # upstream discharge Q and downstream stage h.
            h_new, hu_new = self.step_preissmann(
                dt,
                enforce_bc=True,
                Q_in=Q_target,
                h_out=h_downstream,
            )

            # For uniform-flow targets, pin the upstream stage to the normal-depth
            # guess instead of incorrectly copying the downstream stage.
            if uniform_target_profile:
                h_new[0] = h_upstream_guess

            # 
            self.h = h_new
            self.hu = hu_new

            #  
            # 
            self._apply_pump_internal_bc(conserve_local_flow=False)

            # 
            pump_mask = self._get_pump_region_mask()

            # 
            # 
            # 
            if pump_mask.any():
                # 
                self.hu[~pump_mask] = Q_target / self.B
            else:
                # 
                self.hu[:] = Q_target / self.B

            # 
            # Q_target
            if self.structure_indices:
                self._apply_internal_bc(t=self.current_time, Q_target=Q_target,
                                      max_iter=20, tol=0.05, relax=0.3)  # P2:  (0.6→0.3)

            #
            dh_diff = np.abs(self.h - h_old)
            dhu_diff = np.abs(self.hu - hu_old)
            dh_max = np.nanmax(dh_diff) if np.any(np.isfinite(dh_diff)) else 1e10
            dhu_max = np.nanmax(dhu_diff) if np.any(np.isfinite(dhu_diff)) else 1e10

            if iteration % 500 == 0 and verbose:
                Q_actual = np.mean(self.get_Q())
                Q_error = abs(Q_actual - Q_target) / Q_target * 100
                print(f"   {iteration}: dh={dh_max:.4e}, dhu={dhu_max:.4e}, Q={Q_actual:.3f} ({Q_error:.2f}%)")

            if dh_max < convergence_tol and dhu_max < convergence_tol:
                if verbose:
                    print(f"   {iteration}")
                break
        # 
        Q_final = self.get_Q()
        Q_mean = np.mean(Q_final)
        Q_error = abs(Q_mean - Q_target) / Q_target * 100

        result = {
            'converged': iteration < max_iterations - 1,
            'iterations': iteration,
            'h': self.h.copy(),
            'Q': Q_final.copy(),
            'Q_mean': Q_mean,
            'Q_error_percent': Q_error,
            'dh_max': dh_max,
            'dhu_max': dhu_max
        }

        if verbose:
            print(f"\n")
            print(f"  {Q_mean:.3f} m³/s{Q_error:.2f}%")
            print(f"  [{self.h.min():.3f}, {self.h.max():.3f}] m")

        return result

    def get_Q(self) -> np.ndarray:
        """ (m³/s)"""
        return self.hu * self.B

    def set_Q(self, Q: np.ndarray):
        """ (m³/s)"""
        self.hu = Q / self.B

    Q = property(get_Q, set_Q)

    def compute_cfl_timestep(self, CFL_number: float = 0.5) -> float:
        """
        CFL

        CFL: Δt ≤ CFL * Δx / (|u| + c)
         c = √(gh) 

        Args:
            CFL_number: CFL0.50.2-0.9

        Returns:
            dt:  (s)
        """
        # 
        u = np.abs(self.hu / (self.h + 1e-6))

        #  c = sqrt(gh)
        c = np.sqrt(self.g * (self.h + 1e-6))

        # 
        max_char_speed = np.max(u + c)

        # CFL
        if max_char_speed > 1e-6:
            dt_cfl = CFL_number * self.dx / max_char_speed
        else:
            dt_cfl = 1.0  # 

        return dt_cfl

    def solve_transient(
        self,
        t_end: float,
        dt: float = 0.1,
        Q_upstream: float = None,
        h_downstream: float = None,
        Q_upstream_func: callable = None,
        h_downstream_func: callable = None,
        save_interval: int = 10,
        verbose: bool = True
    ) -> dict:
        """
        

        Args:
            t_end:  (s)
            dt:  (s)
            Q_upstream:  (m³/s)
            h_downstream:  (m)
            Q_upstream_func:  Q(t)
            h_downstream_func:  h(t)
            save_interval: N
            verbose: 

        Returns:
            result: 
        """
        # 
        self.h_history = []
        self.Q_history = []
        self.t_history = []

        # 
        if Q_upstream_func is None:
            Q_upstream_func = lambda t: Q_upstream
        if h_downstream_func is None:
            h_downstream_func = lambda t: h_downstream

        # 
        t = 0.0
        n_steps = int(t_end / dt)

        if verbose:
            print(f"")
            print(f"  : 0 → {t_end} s")
            print(f"  : {dt} s")
            print(f"  : {n_steps}")

        # 
        self.h_history.append(self.h.copy())
        self.Q_history.append(self.get_Q().copy())
        self.t_history.append(t)

        # 
        for step in range(n_steps):
            t = (step + 1) * dt
            self.current_time = t

            # 
            Q_in = Q_upstream_func(t)
            h_out = h_downstream_func(t)

            # flux
            self.set_boundary_conditions(Q_in=Q_in, h_out=h_out)

            # Preissmann
            # 
            h_new, hu_new = self.step_preissmann(dt, enforce_bc=True,
                                                Q_in=Q_in, h_out=h_out,
                                                use_pump_mask=False)

            # 
            self.h = h_new
            self.hu = hu_new

            # 
            # v4.1
            self._apply_pump_internal_bc(conserve_local_flow=True)

            # 
            if self.structure_indices:
                self._apply_internal_bc(t=t, Q_target=Q_in,
                                      max_iter=20, tol=0.05, relax=0.6)

            # 
            if (step + 1) % save_interval == 0:
                self.h_history.append(self.h.copy())
                self.Q_history.append(self.get_Q().copy())
                self.t_history.append(t)

            # 
            if verbose and (step + 1) % max(n_steps // 10, 1) == 0:
                Q_mean = np.mean(self.get_Q())
                h_mean = np.mean(self.h)
                print(f"  t={t:.2f}s ({(step+1)/n_steps*100:.1f}%): " +
                      f"Q={Q_mean:.3f} m³/s, h_avg={h_mean:.3f} m")

        # 
        if verbose:
            print(f"\n")
            print(f"  : {len(self.t_history)}")
            print(f"  : {np.mean(self.get_Q()):.3f} m³/s")
            print(f"  : [{self.h.min():.3f}, {self.h.max():.3f}] m")

        result = {
            't_history': np.array(self.t_history),
            'h_history': np.array(self.h_history),
            'Q_history': np.array(self.Q_history),
            'h_final': self.h.copy(),
            'Q_final': self.get_Q().copy(),
            'x': self.x.copy()
        }

        return result

    def solve_transient_adaptive(
        self,
        t_end: float,
        dt_initial: float = 0.1,
        dt_min: float = 0.001,
        dt_max: float = 1.0,
        CFL_number: float = 0.5,
        Q_upstream: float = None,
        h_downstream: float = None,
        Q_upstream_func: callable = None,
        h_downstream_func: callable = None,
        save_interval_time: float = 1.0,
        verbose: bool = True
    ) -> dict:
        """
        

        CFL

        Args:
            t_end:  (s)
            dt_initial:  (s)
            dt_min:  (s)
            dt_max:  (s)
            CFL_number: CFL0.2-0.90.5
            Q_upstream:  (m³/s)
            h_downstream:  (m)
            Q_upstream_func:  Q(t)
            h_downstream_func:  h(t)
            save_interval_time:  (s)
            verbose: 

        Returns:
            result: 
        """
        # 
        self.h_history = []
        self.Q_history = []
        self.t_history = []
        self.dt_history = []  # 

        # 
        if Q_upstream_func is None:
            Q_upstream_func = lambda t: Q_upstream
        if h_downstream_func is None:
            h_downstream_func = lambda t: h_downstream

        t = 0.0
        dt = dt_initial
        step = 0
        next_save_time = 0.0

        if verbose:
            print(f"")
            print(f"  : 0 → {t_end} s")
            print(f"  : {dt_initial} s")
            print(f"  CFL: {CFL_number}")
            print(f"  : [{dt_min}, {dt_max}] s")

        # 
        self.h_history.append(self.h.copy())
        self.Q_history.append(self.get_Q().copy())
        self.t_history.append(t)
        self.dt_history.append(dt)
        next_save_time = save_interval_time

        # 
        while t < t_end:
            step += 1

            # 
            dt_cfl = self.compute_cfl_timestep(CFL_number)
            dt = np.clip(dt_cfl, dt_min, dt_max)

            # 
            if t + dt > t_end:
                dt = t_end - t

            # 
            t_new = t + dt
            self.current_time = t_new

            # 
            Q_in = Q_upstream_func(t_new)
            h_out = h_downstream_func(t_new)

            # 
            self.set_boundary_conditions(Q_in=Q_in, h_out=h_out)

            # Preissmann
            # 
            h_new, hu_new = self.step_preissmann(dt, enforce_bc=True,
                                                Q_in=Q_in, h_out=h_out,
                                                use_pump_mask=False)

            # 
            self.h = h_new
            self.hu = hu_new

            # 
            # v4.1
            self._apply_pump_internal_bc(conserve_local_flow=True)

            # 
            if self.structure_indices:
                self._apply_internal_bc(t=t_new, Q_target=Q_in,
                                      max_iter=20, tol=0.05, relax=0.6)

            # 
            t = t_new

            # 
            if t >= next_save_time or t >= t_end:
                self.h_history.append(self.h.copy())
                self.Q_history.append(self.get_Q().copy())
                self.t_history.append(t)
                self.dt_history.append(dt)
                next_save_time += save_interval_time

            # 
            if verbose and step % max(1, int(100 / (dt_max/dt_initial))) == 0:
                Q_mean = np.mean(self.get_Q())
                h_mean = np.mean(self.h)
                progress = t / t_end * 100
                print(f"  t={t:.2f}s ({progress:.1f}%), dt={dt:.4f}s: " +
                      f"Q={Q_mean:.3f} m³/s, h_avg={h_mean:.3f} m")

        # 
        if verbose:
            print(f"\n")
            print(f"  : {step}")
            print(f"  : {len(self.t_history)}")
            print(f"  : {np.mean(self.dt_history):.4f} s")
            print(f"  : [{np.min(self.dt_history):.4f}, {np.max(self.dt_history):.4f}] s")
            print(f"  : {np.mean(self.get_Q()):.3f} m³/s")
            print(f"  : [{self.h.min():.3f}, {self.h.max():.3f}] m")

        result = {
            't_history': np.array(self.t_history),
            'h_history': np.array(self.h_history),
            'Q_history': np.array(self.Q_history),
            'dt_history': np.array(self.dt_history),
            'h_final': self.h.copy(),
            'Q_final': self.get_Q().copy(),
            'x': self.x.copy(),
            'n_steps': step
        }

        return result


# 
if __name__ == "__main__":
    print("=" * 70)
    print("HydrostaticCanalSolver ")
    print("=" * 70)

    # 
    solver = HydrostaticCanalSolver(
        length=1000.0,
        nx=101,
        B=10.0,
        S0=0.001,
        n=0.025,
        g=9.81
    )

    print(f"\n")
    print(f"  {solver.length} m")
    print(f"  {solver.nx}")
    print(f"  {solver.dx:.2f} m")
    print(f"  {solver.B} m")

    # 
    print(f"\n...")

    F_mass, F_momentum, S_mass, S_momentum = \
        solver.compute_fluxes_and_sources(solver.h, solver.hu, solver.z, solver.dx)

    print(f"  ")
    print(f"    [{F_mass.min():.3f}, {F_mass.max():.3f}] m²/s")
    print(f"    [{F_momentum.min():.3f}, {F_momentum.max():.3f}] m³/s²")

    print(f"  ")
    print(f"    {S_mass.min():.3f} - {S_mass.max():.3f} m/s")
    print(f"    {S_momentum.min():.3f} - {S_momentum.max():.3f} m²/s²")

    # 
    print(f"\n...")
    dt = 0.1
    h_new, hu_new = solver.step_explicit(dt)

    dh_max = np.max(np.abs(h_new - solver.h))
    dhu_max = np.max(np.abs(hu_new - solver.hu))

    print(f"  {dt} s")
    print(f"  max={dh_max:.4e} m")
    print(f"  max={dhu_max:.4e} m²/s")

    print(f"\n[OK] ")
    print("=" * 70)
