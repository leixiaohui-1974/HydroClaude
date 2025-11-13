#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
/ - Ice Jam Dynamics Model


    ∂(h_ice·ρi)/∂t + ∂(h_ice·ρi·ui)/∂x = S_ice_supply - S_ice_jam

    :
    1. Froude: Fr < Fr_critical (≈0.08)
    2. : S0 < 0.001
    3. : h_ice > h_critical

: RIVICE, CRISSP

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple


class IceJamSolver:
    """
    /

    
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        Fr_critical: float = 0.08,      # Froude
        slope_threshold: float = 0.001,  # 
        ice_thick_threshold: float = 0.3  #  ()
    ):
        """
        

        Parameters:
        -----------
        n_cells : int
            
        dx : float
             (m)
        Fr_critical : float
            Froude ()
        slope_threshold : float
            
        ice_thick_threshold : float
             (h_ice/h)
        """
        self.n_cells = n_cells
        self.dx = dx
        self.Fr_critical = Fr_critical
        self.slope_threshold = slope_threshold
        self.ice_thick_threshold = ice_thick_threshold

        # 
        self.h_ice_transport = np.zeros(n_cells)  #  (m)
        self.ice_jam_mask = np.zeros(n_cells, dtype=bool)  # 
        self.ice_jam_thickness = np.zeros(n_cells)  #  (m)

        # 
        self.rho_ice = 917.0     #  kg/m³
        self.rho_water = 1000.0  #  kg/m³
        self.g = 9.81            #  m/s²

        # 
        self.ice_porosity = 0.4  # 
        self.ice_strength = 1e5  #  Pa ()

    def compute_froude_number(
        self,
        u: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        Froude

        Fr = u / sqrt(g*h)

        Parameters:
        -----------
        u : array
             (m/s)
        h : array
             (m)

        Returns:
        --------
        Fr : array
            Froude
        """
        Fr = np.abs(u) / np.sqrt(self.g * h + 1e-6)
        return Fr

    def check_jam_formation_criteria(
        self,
        h: np.ndarray,
        u: np.ndarray,
        h_ice: np.ndarray,
        S0: np.ndarray
    ) -> np.ndarray:
        """
        

        :
        1. Froude: Fr < Fr_critical
        2. : S0 < slope_threshold
        3. : h_ice/h > ice_thick_threshold

        Parameters:
        -----------
        h : array
             (m)
        u : array
             (m/s)
        h_ice : array
             (m)
        S0 : array
            

        Returns:
        --------
        jam_potential : array (bool)
            
        """
        # 1: Froude
        Fr = self.compute_froude_number(u, h)
        cond1 = Fr < self.Fr_critical

        # 2: 
        cond2 = S0 < self.slope_threshold

        # 3: 
        ice_ratio = h_ice / (h + 1e-6)
        cond3 = ice_ratio > self.ice_thick_threshold

        # 
        jam_potential = cond1 & cond2 & cond3

        return jam_potential

    def transport_ice(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        ice_velocity: Optional[np.ndarray] = None
    ):
        """
        

        

        Parameters:
        -----------
        dt : float
             (s)
        u : array
             (m/s)
        h : array
             (m)
        ice_velocity : array, optional
             (m/s)
        """
        if ice_velocity is None:
            # 
            u_ice = u
        else:
            u_ice = ice_velocity

        h_ice_old = self.h_ice_transport.copy()

        # 
        for i in range(1, self.n_cells - 1):
            if u_ice[i] > 0:
                flux_in = u_ice[i-1] * h_ice_old[i-1]
                flux_out = u_ice[i] * h_ice_old[i]
            else:
                flux_in = u_ice[i+1] * h_ice_old[i+1]
                flux_out = u_ice[i] * h_ice_old[i]

            dh_ice = -(flux_out - flux_in) / self.dx * dt
            self.h_ice_transport[i] += dh_ice

        # 
        self.h_ice_transport = np.maximum(self.h_ice_transport, 0.0)

    def update_ice_jam(
        self,
        dt: float,
        h: np.ndarray,
        u: np.ndarray,
        S0: np.ndarray
    ):
        """
        

        Parameters:
        -----------
        dt : float
             (s)
        h : array
             (m)
        u : array
             (m/s)
        S0 : array
            
        """
        # 
        jam_potential = self.check_jam_formation_criteria(
            h, u, self.h_ice_transport, S0
        )

        # 
        # 
        for i in range(self.n_cells):
            if jam_potential[i]:
                # 
                accumulation_rate = self.h_ice_transport[i] / dt  # 
                self.ice_jam_thickness[i] += accumulation_rate * dt

                # 
                self.h_ice_transport[i] = 0.0

                # 
                self.ice_jam_mask[i] = True

            else:
                # : 
                if self.ice_jam_mask[i]:
                    # : 
                    Fr = self.compute_froude_number(u, h)
                    if Fr[i] > self.Fr_critical * 1.5:
                        # 
                        self.h_ice_transport[i] += self.ice_jam_thickness[i]
                        self.ice_jam_thickness[i] = 0.0
                        self.ice_jam_mask[i] = False

    def compute_backwater_effect(
        self,
        h_original: np.ndarray,
        u: np.ndarray,
        Q: np.ndarray,
        manning_n: float,
        width: float
    ) -> np.ndarray:
        """
        

        Manning:
        1.  ()
        2. 

        Parameters:
        -----------
        h_original : array
             (m)
        u : array
             (m/s)
        Q : array
             (m³/s)
        manning_n : float
            Manning
        width : float
             (m)

        Returns:
        --------
        h_backwater : array
             (m)
        """
        h_backwater = h_original.copy()

        # 
        for i in range(self.n_cells):
            if self.ice_jam_mask[i]:
                #  ()
                n_ice = manning_n * 3.0

                #  ()
                h_effective = h_original[i] - self.ice_jam_thickness[i] * (1 - self.ice_porosity)
                h_effective = max(h_effective, 0.1)  # 

                # 
                A_effective = width * h_effective

                # 
                P = width + 2 * h_effective
                R_h = A_effective / P

                # Manning
                # Q = (1/n) * A * R^(2/3) * S^(1/2)
                # : 

                #  ()
                delta_h = self.ice_jam_thickness[i] * 0.5  # 50%

                h_backwater[i] = h_original[i] + delta_h

        return h_backwater

    def compute_ice_force(
        self,
        h: np.ndarray,
        u: np.ndarray
    ) -> np.ndarray:
        """
         ()

        F_ice = F_drag - F_resist

        Parameters:
        -----------
        h : array
             (m)
        u : array
             (m/s)

        Returns:
        --------
        F_ice : array
             (N/m)
        """
        F_ice = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            if self.ice_jam_mask[i]:
                #  ()
                C_d = 0.01  # 
                F_drag = 0.5 * self.rho_water * C_d * u[i]**2 * self.ice_jam_thickness[i]

                #  ()
                F_resist = self.ice_strength / self.dx  # 

                F_ice[i] = F_drag - F_resist

        return F_ice

    def step(
        self,
        dt: float,
        h: np.ndarray,
        u: np.ndarray,
        Q: np.ndarray,
        S0: np.ndarray,
        h_ice_input: Optional[np.ndarray] = None,
        manning_n: float = 0.03,
        width: float = 10.0
    ) -> Dict[str, np.ndarray]:
        """
        

        Parameters:
        -----------
        dt : float
             (s)
        h : array
             (m)
        u : array
             (m/s)
        Q : array
             (m³/s)
        S0 : array
            
        h_ice_input : array, optional
             (m)
        manning_n : float
            Manning
        width : float
             (m)

        Returns:
        --------
        state : dict
            {'h_backwater': array, 'ice_jam_mask': array, 'ice_jam_thickness': array}
        """
        # 
        if h_ice_input is not None:
            self.h_ice_transport += h_ice_input

        # 
        self.transport_ice(dt, u, h)

        # 
        self.update_ice_jam(dt, h, u, S0)

        # 
        h_backwater = self.compute_backwater_effect(
            h, u, Q, manning_n, width
        )

        return self.get_state(h_backwater)

    def get_state(self, h_backwater: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """"""
        state = {
            'h_ice_transport': self.h_ice_transport.copy(),
            'ice_jam_mask': self.ice_jam_mask.copy(),
            'ice_jam_thickness': self.ice_jam_thickness.copy(),
            'ice_jam_locations': np.where(self.ice_jam_mask)[0]
        }

        if h_backwater is not None:
            state['h_backwater'] = h_backwater

        return state

    def get_diagnostics(self, h: np.ndarray, u: np.ndarray) -> Dict:
        """
        

        Returns:
        --------
        diag : dict
            
        """
        Fr = self.compute_froude_number(u, h)
        F_ice = self.compute_ice_force(h, u)

        diag = {
            'froude_number': Fr,
            'ice_jam_count': np.sum(self.ice_jam_mask),
            'total_ice_jam_volume': np.sum(self.ice_jam_thickness) * self.dx,
            'total_transport_ice_volume': np.sum(self.h_ice_transport) * self.dx,
            'ice_force': F_ice,
            'max_jam_thickness': np.max(self.ice_jam_thickness)
        }

        return diag
