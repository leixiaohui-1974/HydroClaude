#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 - Ice Cover Thickness Solver


    Stefan ():
        ρi·Lf·dh/dt = ki·(Tf - Ts)/h - kw·(Tw - Tf)/δw

    :
    - h:  (m)
    - ρi:  (kg/m³)
    - Lf:  (J/kg)
    - ki:  (W/(m·K))
    - kw:  (W/(m·K))
    - Tf:  (0°C)
    - Ts:  (°C)
    - Tw:  (°C)
    - δw:  (m)

: MIKE ICE, CRISSP

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple


class IceCoverSolver:
    """
    

    Stefan
    """

    def __init__(
        self,
        n_cells: int,
        rho_ice: float = 917.0,      #  kg/m³
        L_fusion: float = 3.34e5,    #  J/kg
        k_ice: float = 2.2,          #  W/(m·K)
        k_water: float = 0.6,        #  W/(m·K)
        T_freeze: float = 0.0        #  °C
    ):
        """
        

        Parameters:
        -----------
        n_cells : int
            
        rho_ice : float
             (kg/m³)
        L_fusion : float
             (J/kg)
        k_ice : float
             (W/(m·K))
        k_water : float
             (W/(m·K))
        T_freeze : float
             (°C)
        """
        self.n_cells = n_cells

        # 
        self.rho_ice = rho_ice
        self.L_fusion = L_fusion
        self.k_ice = k_ice
        self.k_water = k_water
        self.T_freeze = T_freeze

        # 
        self.h_ice = np.zeros(n_cells)          #  (m)
        self.ice_fraction = np.zeros(n_cells)   #  (0-1)

        # 
        self.delta_bl = 0.01  #  m

    def initialize(
        self,
        h_ice_initial: Optional[np.ndarray] = None,
        ice_fraction_initial: Optional[np.ndarray] = None
    ):
        """
        

        Parameters:
        -----------
        h_ice_initial : array, optional
             (m)
        ice_fraction_initial : array, optional
             (0-1)
        """
        if h_ice_initial is not None:
            self.h_ice = h_ice_initial.copy()

        if ice_fraction_initial is not None:
            self.ice_fraction = ice_fraction_initial.copy()

    def compute_surface_temperature(
        self,
        T_air: float,
        h_ice: np.ndarray,
        Q_solar: float = 0.0
    ) -> np.ndarray:
        """
        

        : 
            ki*(Tf - Ts)/h = h_air*(Ts - Ta) + ε*σ*Ts⁴

        :
            Ts ≈ (Ta + Tf)/2  ()

        Parameters:
        -----------
        T_air : float
             (°C)
        h_ice : array
             (m)
        Q_solar : float
             (W/m²), 

        Returns:
        --------
        T_surface : array
             (°C)
        """
        # : 
        # ()
        T_surface = np.full(len(h_ice), 0.5 * (T_air + self.T_freeze))
        T_surface = np.minimum(T_surface, self.T_freeze)

        return T_surface

    def solve_stefan_equation(
        self,
        dt: float,
        T_air: float,
        T_water: np.ndarray,
        h_ice: np.ndarray
    ) -> np.ndarray:
        """
        Stefan

        ρi·Lf·dh/dt = ki·(Tf - Ts)/h - kw·(Tw - Tf)/δw

        Parameters:
        -----------
        dt : float
             (s)
        T_air : float
             (°C)
        T_water : array
             (°C)
        h_ice : array
             (m)

        Returns:
        --------
        h_ice_new : array
             (m)
        """
        h_ice_new = h_ice.copy()

        # 
        T_surface = self.compute_surface_temperature(T_air, h_ice)

        for i in range(self.n_cells):
            # 
            if h_ice[i] > 1e-6:
                # /

                #  ()
                Q_up = self.k_ice * (self.T_freeze - T_surface[i]) / h_ice[i]

                #  ()
                Q_down = self.k_water * (T_water[i] - self.T_freeze) / self.delta_bl

                #  ()
                Q_net = Q_up - Q_down

                # 
                dh_dt = Q_net / (self.rho_ice * self.L_fusion)

                # 
                h_ice_new[i] = h_ice[i] + dh_dt * dt

                # 
                if h_ice_new[i] < 0:
                    h_ice_new[i] = 0.0
                    self.ice_fraction[i] = 0.0

            else:
                # 
                if T_water[i] <= self.T_freeze and T_air < 0:
                    #  (1mm)
                    h_ice_new[i] = 0.001  # 1mm
                    self.ice_fraction[i] = 0.1  # 10%
                else:
                    h_ice_new[i] = 0.0

        return h_ice_new

    def update_ice_fraction(
        self,
        h_ice: np.ndarray,
        T_water: np.ndarray
    ):
        """
        

        :
        - h > 0.1m: 100%
        - 0 < h < 0.1m: 
        - h = 0: 0%

        Parameters:
        -----------
        h_ice : array
             (m)
        T_water : array
             (°C)
        """
        for i in range(self.n_cells):
            if h_ice[i] >= 0.1:
                self.ice_fraction[i] = 1.0
            elif h_ice[i] > 0:
                self.ice_fraction[i] = h_ice[i] / 0.1  # 
            else:
                self.ice_fraction[i] = 0.0

    def step(
        self,
        dt: float,
        T_air: float,
        T_water: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        

        Parameters:
        -----------
        dt : float
             (s)
        T_air : float
             (°C)
        T_water : array
             (°C)

        Returns:
        --------
        state : dict
            {'h_ice': array, 'ice_fraction': array}
        """
        # Stefan
        self.h_ice = self.solve_stefan_equation(dt, T_air, T_water, self.h_ice)

        # 
        self.update_ice_fraction(self.h_ice, T_water)

        return self.get_state()

    def get_state(self) -> Dict[str, np.ndarray]:
        """"""
        return {
            'h_ice': self.h_ice.copy(),
            'ice_fraction': self.ice_fraction.copy()
        }

    def get_diagnostics(self, T_air: float, T_water: np.ndarray) -> Dict[str, np.ndarray]:
        """
        

        Returns:
        --------
        diag : dict
            
        """
        T_surface = self.compute_surface_temperature(T_air, self.h_ice)

        # 
        Q_up = np.zeros(self.n_cells)
        Q_down = np.zeros(self.n_cells)

        mask = self.h_ice > 1e-6
        Q_up[mask] = self.k_ice * (self.T_freeze - T_surface[mask]) / self.h_ice[mask]
        Q_down[mask] = self.k_water * (T_water[mask] - self.T_freeze) / self.delta_bl

        diag = {
            'T_surface': T_surface,
            'heat_flux_up': Q_up,
            'heat_flux_down': Q_down,
            'heat_flux_net': Q_up - Q_down,
            'ice_volume': np.sum(self.h_ice),
            'ice_covered_cells': np.sum(self.ice_fraction > 0.01)
        }

        return diag


class StefanAnalyticalSolution:
    """
    Stefan ()

    1D Stefan:
        h(t) = λ * √(2*α*t)

    :
        - α = k/(ρ·cp) 
        - λ Stefan,
    """

    def __init__(
        self,
        T_air: float,      #  (°C)
        T_water: float,    #  (°C)
        rho_ice: float = 917.0,
        L_fusion: float = 3.34e5,
        k_ice: float = 2.2
    ):
        self.T_air = T_air
        self.T_water = T_water
        self.rho_ice = rho_ice
        self.L_fusion = L_fusion
        self.k_ice = k_ice

        # Stefan
        cp_ice = 2108.0  # J/(kg·K)
        self.alpha = k_ice / (rho_ice * cp_ice)

        # Stefan ()
        # 
        self.stefan_constant = self._compute_stefan_constant()

    def _compute_stefan_constant(self) -> float:
        """
        Stefan ()

        ,
        """
        # 
        delta_T = abs(self.T_air)
        lam = np.sqrt(delta_T / 10.0)  # 
        return lam

    def compute_thickness(self, t: float) -> float:
        """
        

        h(t) = λ * √(2*α*t)

        Parameters:
        -----------
        t : float
             (s)

        Returns:
        --------
        h : float
             (m)
        """
        h = self.stefan_constant * np.sqrt(2 * self.alpha * t)
        return h
