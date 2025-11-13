#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 (Phytoplankton Growth Module)

:
-  (Steele + )
-  (MonodNP)
-  ()
- 
- 
-  (Redfield)
- 

: WASP Eutrophication, CE-QUAL-W2 Algae

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple
from solvers.water_quality_adr import ADRSolver


class PhytoplanktonSolver(ADRSolver):
    """
    

    :
    - Chla: a (μg/L)

    :
    - DO: , 
    - NH4, NO3, PO4: 
    - : 

    :
    - WASP: Eutrophication
    - CE-QUAL-W2: Algae
    - MIKE ECO Lab: Phytoplankton
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        # 
        mu_max_20: float = 2.0,      #  @ 20°C (1/day)
        K_N: float = 0.025,          #  (mg N/L)
        K_P: float = 0.001,          #  (mg P/L)
        I_s: float = 100.0,          #  (W/m²)
        k_d: float = 0.05,           #  @ 20°C (1/day)
        k_r: float = 0.05,           #  @ 20°C (1/day)
        k_e: float = 0.15,           #  (1/m)
        vs_algae: float = 0.1,       #  (m/day)
        # Redfield (C:N:P = 106:16:1)
        N_per_Chla: float = 0.08,    # mg N / μg Chla
        P_per_Chla: float = 0.005,   # mg P / μg Chla
        O2_per_Chla: float = 0.15,   # mg O2 / μg Chla ()
        # 
        use_numba: bool = True
    ):
        """
        

        Parameters:
        -----------
        n_cells : int
            
        dx : float
             (m)
        mu_max_20 : float
             @ 20°C (1/day)
        K_N : float
             (mg N/L) - 0.01-0.05
        K_P : float
             (mg P/L) - 0.001-0.005
        I_s : float
             (W/m²) - Steele
        k_d : float
             @ 20°C (1/day)
        k_r : float
             @ 20°C (1/day)
        k_e : float
             (1/m) - +
        vs_algae : float
             (m/day)
        N_per_Chla : float
            / (mg N / μg Chla)
        P_per_Chla : float
            / (mg P / μg Chla)
        O2_per_Chla : float
             (mg O2 / μg Chla / day)
        use_numba : bool
            Numba
        """
        super().__init__(n_cells, dx, use_numba=use_numba, use_muscl=True)

        # 
        self.Chla = np.ones(n_cells) * 10.0  # a (μg/L)

        # 
        self.mu_max_20 = mu_max_20
        self.K_N = K_N
        self.K_P = K_P
        self.I_s = I_s
        self.k_d = k_d
        self.k_r = k_r
        self.k_e = k_e
        self.vs_algae = vs_algae

        # 
        self.N_per_Chla = N_per_Chla
        self.P_per_Chla = P_per_Chla
        self.O2_per_Chla = O2_per_Chla

        # 
        self.theta_mu = 1.068   # 
        self.theta_d = 1.045    # 
        self.theta_r = 1.045    # 

        # 
        self.T_opt = 20.0       #  (°C)
        self.T_std = 8.0        #  (°C)

    def initialize(
        self,
        Chla_initial: np.ndarray
    ):
        """
        

        Parameters:
        -----------
        Chla_initial : array
            a (μg/L)
        """
        self.Chla = Chla_initial.copy()

    def compute_light_limitation(
        self,
        I_0: np.ndarray,
        h: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
         (Steele + )

        Steele:
        f_I = (I/I_s) * exp(1 - I/I_s)

        :
        - : ~0.1-0.3 (0.2)
        - : ~0.01-0.05

        Parameters:
        -----------
        I_0 : array
             (W/m²)
        h : array
             (m)
        ice_cover_fraction : array, optional
             (0-1)

        Returns:
        --------
        f_I : array
             (0-1)
        """
        # 
        if ice_cover_fraction is not None:
            #  ()
            ice_transmittance = 0.2
            I_surface = I_0 * (1 - ice_cover_fraction + ice_cover_fraction * ice_transmittance)
        else:
            I_surface = I_0

        #  ()
        # I_avg = I_surface * (1 - exp(-k_e*h)) / (k_e*h)
        k_h = self.k_e * h
        with np.errstate(divide='ignore', invalid='ignore'):
            I_avg = I_surface * (1 - np.exp(-k_h)) / (k_h + 1e-10)
        I_avg = np.where(k_h < 0.01, I_surface, I_avg)  # 

        # Steele
        I_ratio = I_avg / self.I_s
        f_I = I_ratio * np.exp(1 - I_ratio)

        # [0, 1]
        f_I = np.clip(f_I, 0.0, 1.0)

        return f_I

    def compute_nutrient_limitation(
        self,
        NH4: np.ndarray,
        NO3: np.ndarray,
        PO4: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
         (Monod)

        : NH4NO3
        f_N = (NH4 + NO3) / (K_N + NH4 + NO3)

        :
        f_P = PO4 / (K_P + PO4)

        Parameters:
        -----------
        NH4 : array
             (mg/L)
        NO3 : array
             (mg/L)
        PO4 : array
             (mg/L)

        Returns:
        --------
        f_N : array
             (0-1)
        f_P : array
             (0-1)
        """
        #  ()
        TIN = NH4 + NO3
        f_N = TIN / (self.K_N + TIN)

        # 
        f_P = PO4 / (self.K_P + PO4)

        return f_N, f_P

    def compute_temperature_limitation(
        self,
        T: np.ndarray
    ) -> np.ndarray:
        """
        

        :
        f_T = exp(-((T - T_opt) / T_std)²)

        Parameters:
        -----------
        T : array
             (°C)

        Returns:
        --------
        f_T : array
             (0-1)
        """
        # 
        f_T = np.exp(-((T - self.T_opt) / self.T_std)**2)

        return f_T

    def compute_growth_rate(
        self,
        Chla: np.ndarray,
        I_0: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        NH4: np.ndarray,
        NO3: np.ndarray,
        PO4: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        

        Growth = mu_max * f_I * f_N * f_P * f_T * Chla

        Parameters:
        -----------
        Chla : array
            a (μg/L)
        I_0 : array
             (W/m²)
        h : array
             (m)
        T : array
             (°C)
        NH4, NO3, PO4 : array
             (mg/L)
        ice_cover_fraction : array, optional
            

        Returns:
        --------
        growth_rate : array
             (μg/L/day)
        diagnostics : dict
             (f_I, f_N, f_P, f_T, mu)
        """
        # 
        mu_max_T = self.mu_max_20 * self.theta_mu**(T - 20)

        # 
        f_I = self.compute_light_limitation(I_0, h, ice_cover_fraction)

        # 
        f_N, f_P = self.compute_nutrient_limitation(NH4, NO3, PO4)

        # 
        f_T = self.compute_temperature_limitation(T)

        # 
        mu = mu_max_T * f_I * np.minimum(f_N, f_P) * f_T

        # 
        growth_rate = mu * Chla

        # 
        diagnostics = {
            'f_I': f_I,
            'f_N': f_N,
            'f_P': f_P,
            'f_T': f_T,
            'mu': mu,
            'limiting_factor': self._identify_limiting_factor(f_I, f_N, f_P)
        }

        return growth_rate, diagnostics

    def _identify_limiting_factor(
        self,
        f_I: np.ndarray,
        f_N: np.ndarray,
        f_P: np.ndarray
    ) -> np.ndarray:
        """
        

        Returns:
        --------
        limiting : array of strings
            'Light', 'Nitrogen', 'Phosphorus'
        """
        limiting = np.empty(len(f_I), dtype=object)

        for i in range(len(f_I)):
            if f_I[i] < min(f_N[i], f_P[i]):
                limiting[i] = 'Light'
            elif f_N[i] < f_P[i]:
                limiting[i] = 'Nitrogen'
            else:
                limiting[i] = 'Phosphorus'

        return limiting

    def compute_death_rate(
        self,
        Chla: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        

        Death = k_d * θ^(T-20) * Chla

        Parameters:
        -----------
        Chla : array
            a (μg/L)
        T : array
             (°C)

        Returns:
        --------
        death_rate : array
             (μg/L/day)
        """
        # 
        k_d_T = self.k_d * self.theta_d**(T - 20)

        # 
        death_rate = k_d_T * Chla

        return death_rate

    def compute_respiration_rate(
        self,
        Chla: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
         ()

        Respiration = k_r * θ^(T-20) * Chla

        Parameters:
        -----------
        Chla : array
            a (μg/L)
        T : array
             (°C)

        Returns:
        --------
        respiration_rate : array
             (μg/L/day)
        """
        # 
        k_r_T = self.k_r * self.theta_r**(T - 20)

        # 
        respiration_rate = k_r_T * Chla

        return respiration_rate

    def compute_settling(
        self,
        Chla: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        

        Parameters:
        -----------
        Chla : array
            a (μg/L)
        h : array
             (m)

        Returns:
        --------
        settling_rate : array
             (μg/L/day)
        """
        settling_rate = -self.vs_algae * Chla / h

        return settling_rate

    def compute_nutrient_uptake(
        self,
        growth_rate: np.ndarray,
        NH4: np.ndarray,
        NO3: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        

        Redfield:
        N uptake = N_per_Chla * growth_rate
        P uptake = P_per_Chla * growth_rate

        NH4NO3

        Parameters:
        -----------
        growth_rate : array
             (μg/L/day)
        NH4 : array
             (mg/L)
        NO3 : array
             (mg/L)

        Returns:
        --------
        NH4_uptake : array
            NH4 (mg/L/day)
        NO3_uptake : array
            NO3 (mg/L/day)
        PO4_uptake : array
            PO4 (mg/L/day)
        """
        # 
        N_demand = self.N_per_Chla * growth_rate

        # NH4
        NH4_uptake = np.minimum(NH4 * 10.0, N_demand)  # 
        N_remaining = N_demand - NH4_uptake

        # NO3
        NO3_uptake = np.minimum(NO3 * 10.0, N_remaining)

        # 
        PO4_uptake = self.P_per_Chla * growth_rate

        return NH4_uptake, NO3_uptake, PO4_uptake

    def compute_oxygen_production(
        self,
        growth_rate: np.ndarray,
        respiration_rate: np.ndarray
    ) -> np.ndarray:
        """
        DO/

        : O2_production = O2_per_Chla * growth_rate
        : O2_consumption = O2_per_Chla * respiration_rate

        Parameters:
        -----------
        growth_rate : array
             (μg/L/day)
        respiration_rate : array
             (μg/L/day)

        Returns:
        --------
        DO_change : array
            DO (mg/L/day)
        """
        # 
        O2_production = self.O2_per_Chla * growth_rate

        # 
        O2_consumption = self.O2_per_Chla * respiration_rate

        # DO
        DO_change = O2_production - O2_consumption

        return DO_change

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        I_0: np.ndarray,
        NH4: np.ndarray,
        NO3: np.ndarray,
        PO4: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> Dict:
        """
        

        Parameters:
        -----------
        dt : float
             (s)
        u : array
             (m/s)
        h : array
             (m)
        T : array
             (°C)
        I_0 : array
             (W/m²)
        NH4, NO3, PO4 : array
             (mg/L)
        ice_cover_fraction : array, optional
             (0-1)

        Returns:
        --------
        state : dict
            {'Chla': ,
             'growth_rate': ,
             'death_rate': ,
             'NH4_uptake': NH4,
             'NO3_uptake': NO3,
             'PO4_uptake': PO4,
             'DO_production': DO,
             'diagnostics': }
        """
        # 
        D_L = self.compute_dispersion_coefficient(u, h)

        # 
        def reaction_function(C, dt_react):
            #  (1/day)
            # 
            mu_max_T = self.mu_max_20 * self.theta_mu**(T - 20)

            # 
            f_I = self.compute_light_limitation(I_0, h, ice_cover_fraction)

            # 
            f_N, f_P = self.compute_nutrient_limitation(NH4, NO3, PO4)

            # 
            f_T = self.compute_temperature_limitation(T)

            # 
            mu = mu_max_T * f_I * np.minimum(f_N, f_P) * f_T

            # 
            k_d_T = self.k_d * self.theta_d**(T - 20)

            # 
            k_r_T = self.k_r * self.theta_r**(T - 20)

            # 
            k_s = self.vs_algae / h

            #  (1/day -> 1/s)
            k_net = (mu - k_d_T - k_r_T - k_s) / 86400.0

            # 
            R = k_net * C

            return R

        # Strang
        self.Chla = self.strang_splitting_step(
            dt, self.Chla, u, h, D_L, reaction_function
        )

        # 
        self.Chla = np.maximum(self.Chla, 0.0)

        #  ()
        growth_rate, diagnostics = self.compute_growth_rate(
            self.Chla, I_0, h, T, NH4, NO3, PO4, ice_cover_fraction
        )
        death_rate = self.compute_death_rate(self.Chla, T)
        respiration_rate = self.compute_respiration_rate(self.Chla, T)

        NH4_uptake, NO3_uptake, PO4_uptake = self.compute_nutrient_uptake(
            growth_rate, NH4, NO3
        )

        DO_production = self.compute_oxygen_production(growth_rate, respiration_rate)

        return {
            'Chla': self.Chla,
            'growth_rate': growth_rate,
            'death_rate': death_rate,
            'respiration_rate': respiration_rate,
            'NH4_uptake': NH4_uptake,
            'NO3_uptake': NO3_uptake,
            'PO4_uptake': PO4_uptake,
            'DO_production': DO_production,
            'diagnostics': diagnostics
        }

    def get_state(self) -> Dict:
        """
        

        Returns:
        --------
        state : dict
            
        """
        return {
            'Chla': self.Chla.copy()
        }
