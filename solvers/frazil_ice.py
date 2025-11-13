#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Frazil Ice - Frazil Ice Multi-Size-Class Model


    ∂Ni/∂t + u·∂Ni/∂x - ws,i·∂Ni/∂z = ∂/∂x(εt·∂Ni/∂x) + Si

    :
    - Ni: i (#/m³)
    - ws,i:  (m/s)
    - εt:  (m²/s)
    - Si:  (///)

:
    1. : Np = C1 · ΔT^α · (u/h)^β
    2. : Ns = C2 · Σ(Ni·Vi·di) · ΔT
    3. : dri/dt = Nu·λi·ΔT / (ρi·Lf·ri)
    4. : Jij = αflocc · G · Ni·Nj · (ri+rj)³
    5. : ws = (2/9) · g · (ρi-ρw) · ri² / μ

: MIKE ICE Frazil, CRISSP

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple

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


class FrazilIceSolver:
    """
    Frazil Ice

    
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        n_size_classes: int = 10,
        r_min: float = 1e-5,    #  10 μm
        r_max: float = 1e-2,    #  10 mm
        use_numba: bool = True
    ):
        """
        Frazil Ice

        Parameters:
        -----------
        n_cells : int
            
        dx : float
             (m)
        n_size_classes : int
            
        r_min : float
             (m)
        r_max : float
             (m)
        use_numba : bool
            Numba
        """
        self.n_cells = n_cells
        self.dx = dx
        self.n_classes = n_size_classes
        self.use_numba = use_numba and NUMBA_AVAILABLE

        # bins ()
        self.r_bins = np.logspace(
            np.log10(r_min), np.log10(r_max), n_size_classes
        )

        # bin
        self.r_edges = np.logspace(
            np.log10(r_min), np.log10(r_max), n_size_classes + 1
        )

        # :  N[cell, size_class]
        self.N = np.zeros((n_cells, n_size_classes))

        # 
        self.rho_ice = 917.0     #  kg/m³
        self.rho_water = 1000.0  #  kg/m³
        self.L_fusion = 3.34e5   #  J/kg
        self.k_ice = 2.2         #  W/(m·K)
        self.T_freeze = 0.0      #  °C
        self.g = 9.81            #  m/s²
        self.nu = 1e-6           #  m²/s @ 0°C
        self.Pr = 13.4           # Prandtl @ 0°C

        #  ()
        self.C_primary = 1e6     #  (#/m³/s)
        self.alpha_nucleation = 2.0  # 
        self.beta_nucleation = 0.5   # 

        self.C_secondary = 1e3   # 

        # 
        self.alpha_flocc = 0.25  # 
        self.break_prob = 0.1    # 

        # 
        self.epsilon_t_base = 1e-3  #  m²/s³

    def initialize(self, N_initial: Optional[np.ndarray] = None):
        """
        

        Parameters:
        -----------
        N_initial : array (n_cells, n_classes), optional
            
        """
        if N_initial is not None:
            self.N = N_initial.copy()
        else:
            self.N = np.zeros((self.n_cells, self.n_classes))

    def compute_primary_nucleation(
        self,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        

        : Np = C1 · ΔT^α · (u/h)^β

        Parameters:
        -----------
        T : array
             (°C)
        u : array
             (m/s)
        h : array
             (m)

        Returns:
        --------
        N_primary : array
             (#/m³/s), 
        """
        # 
        delta_T = np.maximum(self.T_freeze - T, 0.0)

        # 
        turbulence = np.abs(u) / (h + 1e-6)

        #  ()
        N_primary = np.zeros(self.n_cells)
        mask = delta_T > 0

        N_primary[mask] = (
            self.C_primary
            * delta_T[mask]**self.alpha_nucleation
            * turbulence[mask]**self.beta_nucleation
        )

        return N_primary

    def compute_secondary_nucleation(
        self,
        T: np.ndarray
    ) -> np.ndarray:
        """
        

        : Ns = C2 · Σ(Ni·Vi·di) · ΔT

        Parameters:
        -----------
        T : array
             (°C)

        Returns:
        --------
        N_secondary : array
             (#/m³/s)
        """
        # 
        delta_T = np.maximum(self.T_freeze - T, 0.0)

        # 
        N_secondary = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            if delta_T[i] > 0:
                # 
                total_volume_number = 0.0
                for j in range(self.n_classes):
                    V_j = (4.0/3.0) * np.pi * self.r_bins[j]**3
                    d_j = 2.0 * self.r_bins[j]
                    total_volume_number += self.N[i, j] * V_j * d_j

                N_secondary[i] = self.C_secondary * total_volume_number * delta_T[i]

        return N_secondary

    def compute_growth_rate(
        self,
        T: np.ndarray,
        u: np.ndarray
    ) -> np.ndarray:
        """
        

        : dri/dt = Nu·λi·ΔT / (ρi·Lf·ri)
              Nu = 2 + 0.6·Re^0.5·Pr^0.33

        Parameters:
        -----------
        T : array
             (°C)
        u : array
             (m/s)

        Returns:
        --------
        dr_dt : array (n_cells, n_classes)
             (m/s)
        """
        # 
        delta_T = np.maximum(self.T_freeze - T, 0.0)

        # 
        dr_dt = np.zeros((self.n_cells, self.n_classes))

        for i in range(self.n_cells):
            if delta_T[i] > 0:
                for j in range(self.n_classes):
                    r_j = self.r_bins[j]

                    # Reynolds
                    Re = 2.0 * r_j * np.abs(u[i]) / self.nu

                    # Nusselt
                    Nu = 2.0 + 0.6 * Re**0.5 * self.Pr**0.33

                    # 
                    dr_dt[i, j] = (
                        Nu * self.k_ice * delta_T[i]
                        / (self.rho_ice * self.L_fusion * r_j)
                    )

        return dr_dt

    def compute_flocculation(
        self,
        u: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        

        : Jij = αflocc · G · Ni·Nj · (ri+rj)³
              G = (εt/ν)^0.5  ()

        Parameters:
        -----------
        u : array
             (m/s)
        h : array
             (m)

        Returns:
        --------
        dN_flocc : array (n_cells, n_classes)
             (#/m³/s)
        """
        dN_flocc = np.zeros((self.n_cells, self.n_classes))

        for i in range(self.n_cells):
            #  ()
            epsilon_t = self.epsilon_t_base * (np.abs(u[i])**3 / h[i])

            # 
            G = np.sqrt(epsilon_t / self.nu)

            # 
            for j in range(self.n_classes - 1):
                for k in range(j + 1, self.n_classes):
                    # 
                    collision_kernel = (
                        self.alpha_flocc * G
                        * (self.r_bins[j] + self.r_bins[k])**3
                    )

                    # 
                    collision_rate = (
                        collision_kernel
                        * self.N[i, j]
                        * self.N[i, k]
                    )

                    # 
                    dN_flocc[i, j] -= collision_rate
                    dN_flocc[i, k] -= collision_rate

                    #  ()
                    if k < self.n_classes - 1:
                        dN_flocc[i, k + 1] += collision_rate

        return dN_flocc

    def compute_settling_velocity(self) -> np.ndarray:
        """
         (Stokes)

        ws = (2/9) · g · (ρi - ρw) · ri² / μ

        Returns:
        --------
        ws : array (n_classes,)
             (m/s)
        """
        # 
        mu = self.nu * self.rho_water

        # Stokes
        ws = (
            (2.0 / 9.0) * self.g
            * (self.rho_water - self.rho_ice)  # : , ws()
            * self.r_bins**2
            / mu
        )

        return ws

    def compute_melting(
        self,
        T: np.ndarray,
        dt: float
    ):
        """
         ()

        Parameters:
        -----------
        T : array
             (°C)
        dt : float
             (s)
        """
        # : 
        mask = T > self.T_freeze

        self.N[mask, :] = 0.0

    def transport_frazil(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        D_t: np.ndarray
    ):
        """
        frazil ice (-)

         + 

        Parameters:
        -----------
        dt : float
             (s)
        u : array
             (m/s)
        h : array
             (m)
        D_t : array
             (m²/s)
        """
        # 
        ws = self.compute_settling_velocity()

        # 
        for j in range(self.n_classes):
            N_old = self.N[:, j].copy()

            #  ()
            dN_conv = np.zeros(self.n_cells)
            for i in range(1, self.n_cells - 1):
                if u[i] > 0:
                    dN_conv[i] = -u[i] * (N_old[i] - N_old[i-1]) / self.dx
                else:
                    dN_conv[i] = -u[i] * (N_old[i+1] - N_old[i]) / self.dx

            #  ()
            dN_diff = np.zeros(self.n_cells)
            for i in range(1, self.n_cells - 1):
                dN_diff[i] = (
                    D_t[i] * (N_old[i+1] - 2*N_old[i] + N_old[i-1]) / self.dx**2
                )

            #  (, )
            # ws < 0 
            dN_settling = -np.abs(ws[j]) * N_old / (h + 1e-6)

            # 
            self.N[:, j] += dt * (dN_conv + dN_diff + dN_settling)

            # 
            self.N[:, j] = np.maximum(self.N[:, j], 0.0)

    def step(
        self,
        dt: float,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        D_t: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        

        :
        1. 
        2. 
        3. 
        4. 
        5. 

        Parameters:
        -----------
        dt : float
             (s)
        T : array
             (°C)
        u : array
             (m/s)
        h : array
             (m)
        D_t : array, optional
             (m²/s)

        Returns:
        --------
        state : dict
            
        """
        if D_t is None:
            # Elder
            u_star = np.abs(u) * 0.03 / h**(1.0/6.0)
            D_t = 5.93 * h * u_star

        # ========== Step 1:  ==========
        #  ()
        N_primary = self.compute_primary_nucleation(T, u, h)
        self.N[:, 0] += N_primary * dt

        #  ()
        N_secondary = self.compute_secondary_nucleation(T)
        self.N[:, 0] += N_secondary * dt

        # ========== Step 2:  ==========
        dr_dt = self.compute_growth_rate(T, u)

        #  ()
        for i in range(self.n_cells):
            for j in range(self.n_classes - 1):
                if dr_dt[i, j] > 0:
                    # 
                    r_new = self.r_bins[j] + dr_dt[i, j] * dt

                    # , 
                    if r_new > self.r_edges[j+1]:
                        transfer_fraction = 0.5  # : 50%
                        transfer_N = self.N[i, j] * transfer_fraction

                        self.N[i, j] -= transfer_N
                        self.N[i, j+1] += transfer_N

        # ========== Step 3:  ==========
        dN_flocc = self.compute_flocculation(u, h)
        self.N += dN_flocc * dt
        self.N = np.maximum(self.N, 0.0)

        # ========== Step 4:  ==========
        self.transport_frazil(dt, u, h, D_t)

        # ========== Step 5:  ==========
        self.compute_melting(T, dt)

        return self.get_state()

    def get_state(self) -> Dict[str, np.ndarray]:
        """"""
        return {
            'N': self.N.copy(),
            'r_bins': self.r_bins,
            'total_number': np.sum(self.N, axis=1),
            'total_volume': self.compute_total_volume(),
            'mean_diameter': self.compute_mean_diameter()
        }

    def compute_total_volume(self) -> np.ndarray:
        """
        

        Returns:
        --------
        phi : array
             ()
        """
        phi = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            total_volume = 0.0
            for j in range(self.n_classes):
                V_j = (4.0/3.0) * np.pi * self.r_bins[j]**3
                total_volume += self.N[i, j] * V_j

            phi[i] = total_volume

        return phi

    def compute_mean_diameter(self) -> np.ndarray:
        """
         ()

        Returns:
        --------
        d_mean : array
             (m)
        """
        d_mean = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            total_N = np.sum(self.N[i, :])
            if total_N > 1e-6:
                # 
                d_mean[i] = np.sum(self.N[i, :] * 2*self.r_bins) / total_N
            else:
                d_mean[i] = 0.0

        return d_mean

    def get_diagnostics(self, T: np.ndarray, u: np.ndarray, h: np.ndarray) -> Dict:
        """
        

        Returns:
        --------
        diag : dict
            
        """
        diag = {
            'total_number_density': np.sum(self.N, axis=1),
            'total_ice_volume_fraction': self.compute_total_volume(),
            'mean_diameter': self.compute_mean_diameter(),
            'primary_nucleation_rate': self.compute_primary_nucleation(T, u, h),
            'secondary_nucleation_rate': self.compute_secondary_nucleation(T),
            'settling_velocity': self.compute_settling_velocity(),
            'size_distribution': self.N.copy()
        }

        return diag
