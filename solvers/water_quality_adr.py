#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ADR - Advection-Diffusion-Reaction Solver


    ∂C/∂t + u·∂C/∂x = ∂/∂x(DL·∂C/∂x) + R(C) + S

    :
    - C:  (mg/L)
    - u:  (m/s)
    - DL:  (m²/s)
    - R(C):  (mg/L/s)
    - S:  (mg/L/s)


    - : MUSCL + 
    - : 
    - :  (Strang Splitting)
    - : TVD-RK2

: WASP, EFDC

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Tuple, Dict, Optional, Callable

# Numba
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


class ADRSolver:
    """
    --

    :
    -  (DO)
    -  (BOD, COD)
    -  (NH4, NO3, PO4)
    -  (Pb, Cd, Hg)
    - 
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        use_numba: bool = True,
        use_muscl: bool = True
    ):
        """
        ADR

        Parameters:
        -----------
        n_cells : int
            
        dx : float
             (m)
        use_numba : bool
            Numba
        use_muscl : bool
            MUSCL ()
        """
        self.n_cells = n_cells
        self.dx = dx
        self.use_numba = use_numba and NUMBA_AVAILABLE
        self.use_muscl = use_muscl

    def compute_dispersion_coefficient(
        self,
        h: np.ndarray,
        u: np.ndarray,
        u_star: Optional[np.ndarray] = None,
        manning_n: float = 0.03
    ) -> np.ndarray:
        """
        

        Elder (1959) :
            DL = 5.93 * h * u*

        Parameters:
        -----------
        h : array
             (m)
        u : array
             (m/s)
        u_star : array, optional
             (m/s), 
        manning_n : float
            Manning

        Returns:
        --------
        D_L : array
             (m²/s)
        """
        if u_star is None:
            # : u* = u * n / h^(1/6)
            u_star = np.abs(u) * manning_n / h**(1.0/6.0)

        # Elder
        D_L = 5.93 * h * u_star

        #  ()
        D_molecular = 1e-9  # m²/s
        D_L += D_molecular

        return D_L

    def minmod_limiter(self, r: np.ndarray) -> np.ndarray:
        """Minmod"""
        return np.maximum(0.0, np.minimum(1.0, r))

    def muscl_reconstruction(
        self,
        C: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        MUSCL

        Parameters:
        -----------
        C : array
            

        Returns:
        --------
        C_L, C_R : array
            
        """
        n = len(C)
        C_L = np.zeros(n+1)
        C_R = np.zeros(n+1)

        # 
        for i in range(1, n):
            # 
            if i > 0:
                dC_up = C[i] - C[i-1]
            else:
                dC_up = 0.0

            # 
            if i < n-1:
                dC_down = C[i+1] - C[i]
            else:
                dC_down = 0.0

            # 
            if abs(dC_down) > 1e-12:
                r = dC_up / dC_down
            else:
                r = 0.0

            # Minmod
            phi = self.minmod_limiter(np.array([r]))[0]

            # 
            C_L[i] = C[i-1] + 0.5 * phi * dC_up
            C_R[i] = C[i] - 0.5 * phi * dC_down

        # 
        C_L[0] = C[0]
        C_R[0] = C[0]
        C_L[n] = C[n-1]
        C_R[n] = C[n-1]

        return C_L, C_R

    def compute_advective_flux(
        self,
        C: np.ndarray,
        u: np.ndarray
    ) -> np.ndarray:
        """
        

        : F = u * C_upwind

        Parameters:
        -----------
        C : array
            
        u : array
            

        Returns:
        --------
        F : array
             ()
        """
        n = len(C)
        F = np.zeros(n+1)

        if self.use_muscl:
            # MUSCL
            C_L, C_R = self.muscl_reconstruction(C)

            # 
            for i in range(n+1):
                if i < len(u):
                    u_face = u[i]
                else:
                    u_face = u[-1]

                if u_face > 0:
                    F[i] = u_face * C_L[i]
                else:
                    F[i] = u_face * C_R[i]
        else:
            # 
            for i in range(1, n):
                if u[i] > 0:
                    F[i] = u[i] * C[i-1]
                else:
                    F[i] = u[i] * C[i]

            # 
            F[0] = u[0] * C[0]
            F[n] = u[-1] * C[-1]

        return F

    def compute_diffusive_flux(
        self,
        C: np.ndarray,
        D_L: np.ndarray
    ) -> np.ndarray:
        """
        

        : F = -DL * dC/dx

        Parameters:
        -----------
        C : array
            
        D_L : array
            

        Returns:
        --------
        F_diff : array
             ()
        """
        n = len(C)
        F_diff = np.zeros(n+1)

        # 
        for i in range(1, n):
            dC_dx = (C[i] - C[i-1]) / self.dx
            D_face = 0.5 * (D_L[i-1] + D_L[i])
            F_diff[i] = -D_face * dC_dx

        #  ()
        F_diff[0] = 0.0
        F_diff[n] = 0.0

        return F_diff

    def solve_transport(
        self,
        dt: float,
        C: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        D_L: np.ndarray
    ) -> np.ndarray:
        """
         (+)

        ∂C/∂t + ∂F/∂x = 0

        Parameters:
        -----------
        dt : float
             (s)
        C : array
             (mg/L)
        u : array
             (m/s)
        h : array
             (m)
        D_L : array
             (m²/s)

        Returns:
        --------
        C_new : array
             (mg/L)
        """
        # 
        F_adv = self.compute_advective_flux(C, u)

        # 
        F_diff = self.compute_diffusive_flux(C, D_L)

        # 
        F_total = F_adv + F_diff

        # 
        dC_dt = -(F_total[1:] - F_total[:-1]) / self.dx

        # 
        C_new = C + dt * dC_dt

        # 
        C_new = np.maximum(C_new, 0.0)

        return C_new

    def strang_splitting_step(
        self,
        dt: float,
        C: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        D_L: np.ndarray,
        reaction_func: Callable[[np.ndarray, float], np.ndarray],
        source_sink: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        StrangADR

        :
        1. : C* = C^n + 0.5*dt*R(C^n)
        2. : C** = Transport(C*, dt)
        3. : C^(n+1) = C** + 0.5*dt*R(C**)

        Parameters:
        -----------
        dt : float
             (s)
        C : array
             (mg/L)
        u : array
             (m/s)
        h : array
             (m)
        D_L : array
             (m²/s)
        reaction_func : callable
             R(C, dt) -> dC/dt
        source_sink : array, optional
             (mg/L/s)

        Returns:
        --------
        C_new : array
             (mg/L)
        """
        # Step 1: 
        R1 = reaction_func(C, 0.5*dt)
        C_star = C + 0.5*dt*R1

        # 
        if source_sink is not None:
            C_star += 0.5*dt*source_sink

        C_star = np.maximum(C_star, 0.0)

        # Step 2: 
        C_star_star = self.solve_transport(dt, C_star, u, h, D_L)

        # Step 3: 
        R2 = reaction_func(C_star_star, 0.5*dt)
        C_new = C_star_star + 0.5*dt*R2

        # 
        if source_sink is not None:
            C_new += 0.5*dt*source_sink

        C_new = np.maximum(C_new, 0.0)

        return C_new

    def compute_courant_number(
        self,
        dt: float,
        u: np.ndarray
    ) -> float:
        """
        Courant

        CFL = u * dt / dx

        Parameters:
        -----------
        dt : float
             (s)
        u : array
             (m/s)

        Returns:
        --------
        CFL : float
            Courant
        """
        CFL = np.max(np.abs(u)) * dt / self.dx
        return CFL

    def check_stability(
        self,
        dt: float,
        u: np.ndarray,
        D_L: np.ndarray,
        cfl_limit: float = 0.5
    ) -> Tuple[bool, str]:
        """
        

        Parameters:
        -----------
        dt : float
             (s)
        u : array
             (m/s)
        D_L : array
             (m²/s)
        cfl_limit : float
            CFL

        Returns:
        --------
        is_stable : bool
            
        message : str
            
        """
        # CFL
        CFL_adv = self.compute_courant_number(dt, u)

        # CFL
        CFL_diff = np.max(D_L) * dt / self.dx**2

        if CFL_adv > cfl_limit:
            return False, f"CFL={CFL_adv:.3f} > {cfl_limit}, !"

        if CFL_diff > 0.5:
            return False, f"CFL={CFL_diff:.3f} > 0.5, !"

        return True, f" (CFL_adv={CFL_adv:.3f}, CFL_diff={CFL_diff:.3f})"


class ConservativeTracerSolver(ADRSolver):
    """
     ()

    
    """

    def __init__(self, n_cells: int, dx: float, **kwargs):
        super().__init__(n_cells, dx, **kwargs)
        self.C = np.zeros(n_cells)

    def initialize(self, C_initial: np.ndarray):
        """"""
        self.C = C_initial.copy()

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        manning_n: float = 0.03
    ) -> np.ndarray:
        """ (, )"""
        # 
        D_L = self.compute_dispersion_coefficient(h, u, manning_n=manning_n)

        # 
        self.C = self.solve_transport(dt, self.C, u, h, D_L)

        return self.C

    def compute_total_mass(self, h: np.ndarray, width: float) -> float:
        """
         ()

        Parameters:
        -----------
        h : array
             (m)
        width : float
             (m)

        Returns:
        --------
        total_mass : float
             (kg)
        """
        #  = h * width * dx
        volume = h * width * self.dx  # m³

        #  =  *  (mg/L * m³ = g)
        mass = self.C * volume  # mg/L * m³ = mg * 1000 L / L = mg * 1000

        total_mass = np.sum(mass) / 1e6  # kg

        return total_mass
