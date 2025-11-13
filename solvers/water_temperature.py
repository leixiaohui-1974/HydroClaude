#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 - Water Temperature Transport Module


    ∂T/∂t + u·∂T/∂x = ∂/∂x(DT·∂T/∂x) + ST

    :
    - T:  (°C)
    - u:  (m/s)
    - DT:  (m²/s)
    - ST:  (°C/s)
        - 
        - -
        - 

: MIKE ICE, CRISSP

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Tuple, Dict, Optional

# Numba
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    # 
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


class WaterTemperatureSolver:
    """
    

    HydroClaudeGodunov
    
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        thermal_diffusivity: float = 1.4e-7,  #  m²/s @ 20°C
        use_numba: bool = True
    ):
        """
        

        Parameters:
        -----------
        n_cells : int
            
        dx : float
             (m)
        thermal_diffusivity : float
             (m²/s)20°C
        use_numba : bool
            Numba
        """
        self.n_cells = n_cells
        self.dx = dx
        self.D_T = thermal_diffusivity
        self.use_numba = use_numba and NUMBA_AVAILABLE

        # 
        self.T = np.ones(n_cells) * 20.0  # 20°C

        # 
        self.rho_w = 1000.0  #  kg/m³
        self.cp_w = 4186.0   #  J/(kg·K)
        self.T_freeze = 0.0  #  °C

        # 
        self.stefan_boltzmann = 5.67e-8  # Stefan-Boltzmann W/(m²·K⁴)
        self.emissivity = 0.97  # 

    def initialize(self, T_initial: np.ndarray):
        """"""
        if len(T_initial) != self.n_cells:
            raise ValueError(f"{len(T_initial)}{self.n_cells}")
        self.T = T_initial.copy()

    def compute_atmospheric_heat_flux(
        self,
        T_water: np.ndarray,
        T_air: float,
        solar_radiation: float,
        wind_speed: float,
        relative_humidity: float,
        cloud_cover: float = 0.0
    ) -> np.ndarray:
        """
        

        : QUAL2K

        Parameters:
        -----------
        T_water : array
             (°C)
        T_air : float
             (°C)
        solar_radiation : float
             (W/m²)
        wind_speed : float
             (m/s)
        relative_humidity : float
             (0-1)
        cloud_cover : float
             (0-1)

        Returns:
        --------
        Q_net : array
             (W/m²), 
        """
        # 1.  (0.08)
        albedo = 0.08
        Q_solar = solar_radiation * (1 - albedo)

        # 2.  (Stefan-Boltzmann)
        T_w_K = T_water + 273.15
        T_a_K = T_air + 273.15

        #  ()
        emissivity_air = 0.64 + 0.045 * np.sqrt(self._vapor_pressure(T_air, relative_humidity))
        emissivity_air *= (1 + 0.17 * cloud_cover**2)
        Q_atm_longwave = emissivity_air * self.stefan_boltzmann * T_a_K**4

        # 
        Q_back_radiation = self.emissivity * self.stefan_boltzmann * T_w_K**4

        Q_longwave = Q_atm_longwave - Q_back_radiation

        # 3.  (Penman)
        L_v = 2.453e6  #  J/kg @ 20°C
        e_s = self._vapor_pressure(T_water, 1.0)  # 
        e_a = self._vapor_pressure(T_air, relative_humidity)  # 

        #  (Ryan & Harleman, 1973)
        f_wind = 9.2 + 0.46 * wind_speed**2  # W/(m²·mb)
        Q_evaporation = -f_wind * (e_s - e_a)  # 

        # 4.  (Bowen)
        bowen_ratio = 0.61  # /
        Q_convection = bowen_ratio * Q_evaporation * (T_water - T_air) / (e_s - e_a + 1e-6)

        # 
        Q_net = Q_solar + Q_longwave + Q_evaporation + Q_convection

        return Q_net * np.ones(len(T_water))

    def _vapor_pressure(self, T: float, RH: float) -> float:
        """
         (mb)

        Magnus
        """
        e_sat = 6.112 * np.exp(17.67 * T / (T + 243.5))
        return e_sat * RH

    def compute_ice_water_heat_flux(
        self,
        T_water: np.ndarray,
        ice_cover_thickness: np.ndarray,
        ice_cover_fraction: np.ndarray
    ) -> np.ndarray:
        """
        -

        Parameters:
        -----------
        T_water : array
             (°C)
        ice_cover_thickness : array
             (m)
        ice_cover_fraction : array
             (0-1)

        Returns:
        --------
        Q_ice : array
            - (W/m²), 
        """
        # 
        k_ice = 2.2  # W/(m·K)

        # -
        delta_T = T_water - self.T_freeze

        #  (1cm)
        delta_bl = 0.01  # m

        #  ()
        k_water = 0.6  # W/(m·K)
        Q_ice = -k_water * delta_T / delta_bl * ice_cover_fraction

        return Q_ice

    def compute_bed_heat_flux(
        self,
        T_water: np.ndarray,
        T_bed: float = 10.0
    ) -> np.ndarray:
        """
        

        Parameters:
        -----------
        T_water : array
             (°C)
        T_bed : float
             (°C)

        Returns:
        --------
        Q_bed : array
             (W/m²)
        """
        # 
        k_bed = 1.5  # W/(m·K)
        delta_bed = 0.1  #  m

        Q_bed = k_bed * (T_bed - T_water) / delta_bed

        return Q_bed

    def solve_advection_diffusion(
        self,
        dt: float,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        Q_net: np.ndarray
    ) -> np.ndarray:
        """
        -

        ∂T/∂t + u·∂T/∂x = DT·∂²T/∂x² + Q_net/(ρ·cp·h)

        : TVD-MUSCL + 

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
        Q_net : array
             (W/m²)

        Returns:
        --------
        T_new : array
             (°C)
        """
        if self.use_numba:
            return self._solve_advection_diffusion_numba(
                dt, T, u, h, Q_net, self.dx, self.D_T, self.rho_w, self.cp_w
            )
        else:
            return self._solve_advection_diffusion_python(
                dt, T, u, h, Q_net
            )

    def _solve_advection_diffusion_python(
        self,
        dt: float,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        Q_net: np.ndarray
    ) -> np.ndarray:
        """Python"""
        n = len(T)
        T_new = T.copy()

        # 1.  ()
        for i in range(1, n-1):
            if u[i] > 0:
                dT_dx = (T[i] - T[i-1]) / self.dx
            else:
                dT_dx = (T[i+1] - T[i]) / self.dx
            T_new[i] -= dt * u[i] * dT_dx

        # 2.  ()
        for i in range(1, n-1):
            d2T_dx2 = (T[i+1] - 2*T[i] + T[i-1]) / self.dx**2
            T_new[i] += dt * self.D_T * d2T_dx2

        # 3.  ()
        source = Q_net / (self.rho_w * self.cp_w * h)
        T_new += dt * source

        #  ()
        T_new[0] = T_new[1]
        T_new[-1] = T_new[-2]

        return T_new

    @staticmethod
    @njit
    def _solve_advection_diffusion_numba(
        dt: float,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        Q_net: np.ndarray,
        dx: float,
        D_T: float,
        rho_w: float,
        cp_w: float
    ) -> np.ndarray:
        """Numba"""
        n = len(T)
        T_new = T.copy()

        # 1. 
        for i in range(1, n-1):
            if u[i] > 0:
                dT_dx = (T[i] - T[i-1]) / dx
            else:
                dT_dx = (T[i+1] - T[i]) / dx
            T_new[i] -= dt * u[i] * dT_dx

        # 2. 
        for i in range(1, n-1):
            d2T_dx2 = (T[i+1] - 2*T[i] + T[i-1]) / dx**2
            T_new[i] += dt * D_T * d2T_dx2

        # 3. 
        for i in range(n):
            source = Q_net[i] / (rho_w * cp_w * h[i])
            T_new[i] += dt * source

        # 
        T_new[0] = T_new[1]
        T_new[-1] = T_new[-2]

        return T_new

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        T_air: float,
        solar_radiation: float = 500.0,
        wind_speed: float = 2.0,
        relative_humidity: float = 0.6,
        ice_cover_thickness: Optional[np.ndarray] = None,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        

        Parameters:
        -----------
        dt : float
             (s)
        u : array
             (m/s)
        h : array
             (m)
        T_air : float
             (°C)
        solar_radiation : float
             (W/m²)
        wind_speed : float
             (m/s)
        relative_humidity : float
             (0-1)
        ice_cover_thickness : array, optional
             (m)
        ice_cover_fraction : array, optional
             (0-1)

        Returns:
        --------
        T_new : array
             (°C)
        """
        # 
        Q_atm = self.compute_atmospheric_heat_flux(
            self.T, T_air, solar_radiation, wind_speed, relative_humidity
        )

        # -
        if ice_cover_thickness is not None and ice_cover_fraction is not None:
            Q_ice = self.compute_ice_water_heat_flux(
                self.T, ice_cover_thickness, ice_cover_fraction
            )
        else:
            Q_ice = np.zeros(self.n_cells)

        # 
        Q_bed = self.compute_bed_heat_flux(self.T)

        # 
        Q_net = Q_atm + Q_ice + Q_bed

        # ADR
        self.T = self.solve_advection_diffusion(dt, self.T, u, h, Q_net)

        #  ()
        self.T = np.maximum(self.T, self.T_freeze)

        return self.T

    def get_supercooling(self) -> np.ndarray:
        """
         (frazil ice)

        Returns:
        --------
        delta_T : array
             (°C), 
        """
        return np.maximum(self.T_freeze - self.T, 0.0)

    def get_state(self) -> Dict[str, np.ndarray]:
        """"""
        return {
            'T': self.T.copy(),
            'supercooling': self.get_supercooling()
        }
