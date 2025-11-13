#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
(DO) - Dissolved Oxygen Solver


    ∂DO/∂t + u·∂DO/∂x = DL·∂²DO/∂x² + Ka·(DO_sat - DO) - kd·BOD - SOD/h

    :
    - DO:  (mg/L)
    - DO_sat: DO (mg/L), 
    - Ka:  (1/day), 
    - kd: BOD (1/day), 
    - BOD:  (mg/L)
    - SOD:  (g/m²/day)

: QUAL2K DO, WASP DO

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple
from .water_quality_adr import ADRSolver


class DissolvedOxygenSolver(ADRSolver):
    """
    

    DO:
    1. 
    2. BOD
    3.  (SOD)
    4. 
    5.  ()
    6. 
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        kd_20: float = 0.2,      # BOD @ 20°C (1/day)
        SOD_20: float = 1.0,     #  @ 20°C (g/m²/day)
        use_numba: bool = True
    ):
        """
        DO

        Parameters:
        -----------
        n_cells : int
            
        dx : float
             (m)
        kd_20 : float
            BOD @ 20°C (1/day)
        SOD_20 : float
             @ 20°C (g/m²/day)
        use_numba : bool
            Numba
        """
        super().__init__(n_cells, dx, use_numba=use_numba, use_muscl=True)

        # 
        self.DO = np.ones(n_cells) * 8.0   # DO = 8 mg/L
        self.BOD = np.ones(n_cells) * 2.0  # BOD = 2 mg/L

        # DO
        self.kd_20 = kd_20
        self.SOD_20 = SOD_20

        # 
        self.theta_ka = 1.024   # 
        self.theta_kd = 1.047   # BOD
        self.theta_SOD = 1.065  # SOD

    def initialize(
        self,
        DO_initial: np.ndarray,
        BOD_initial: Optional[np.ndarray] = None
    ):
        """
        DOBOD

        Parameters:
        -----------
        DO_initial : array
            DO (mg/L)
        BOD_initial : array, optional
            BOD (mg/L)
        """
        self.DO = DO_initial.copy()
        if BOD_initial is not None:
            self.BOD = BOD_initial.copy()

    def compute_DO_saturation(self, T: np.ndarray) -> np.ndarray:
        """
        DO

        Elmore & Hayes (1960) :
            DO_sat = 14.652 - 0.41022*T + 0.007991*T² - 0.000077774*T³

        Parameters:
        -----------
        T : array
             (°C)

        Returns:
        --------
        DO_sat : array
            DO (mg/L)
        """
        DO_sat = (14.652
                  - 0.41022 * T
                  + 0.007991 * T**2
                  - 0.000077774 * T**3)

        return DO_sat

    def compute_reaeration_coefficient(
        self,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        

        O'Connor-Dobbins (1958) :
            Ka(20) = 3.93 * u^0.5 / h^1.5  (1/day)

        :
            Ka(T) = Ka(20) * 1.024^(T-20)

        :
            Ka_ice = Ka * (1 - 0.9*f_ice)  # 90%

        Parameters:
        -----------
        u : array
             (m/s)
        h : array
             (m)
        T : array
             (°C)
        ice_cover_fraction : array, optional
             (0-1)

        Returns:
        --------
        Ka : array
             (1/day)
        """
        # O'Connor-Dobbins @ 20°C
        Ka_20 = 3.93 * np.abs(u)**0.5 / h**1.5

        # 
        Ka_T = Ka_20 * self.theta_ka**(T - 20)

        # 
        if ice_cover_fraction is not None:
            # 90%
            ice_reduction = 1 - 0.9 * ice_cover_fraction
            Ka_T *= ice_reduction

        return Ka_T

    def compute_BOD_decay(
        self,
        BOD: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        BOD

        kd(T) = kd(20) * 1.047^(T-20)

        Parameters:
        -----------
        BOD : array
            BOD (mg/L)
        T : array
             (°C)

        Returns:
        --------
        decay_rate : array
            BOD (mg/L/day)
        """
        # 
        kd_T = self.kd_20 * self.theta_kd**(T - 20)

        # 
        decay_rate = kd_T * BOD

        return decay_rate

    def compute_sediment_oxygen_demand(
        self,
        h: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        

        SOD(T) = SOD(20) * 1.065^(T-20)  (g/m²/day)

        : SOD/h (mg/L/day)

        Parameters:
        -----------
        h : array
             (m)
        T : array
             (°C)

        Returns:
        --------
        sod_rate : array
             (mg/L/day)
        """
        # 
        SOD_T = self.SOD_20 * self.theta_SOD**(T - 20)

        #  (g/m²/day -> mg/L/day)
        # SOD: g/m²/day
        #  = SOD / h (m) = g/(m³·day) = 1000 mg/(1000 L·day) = mg/L/day
        sod_rate = SOD_T / h  # g/m²/day / m = mg/L/day

        return sod_rate

    def compute_reaction_terms(
        self,
        DO: np.ndarray,
        BOD: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        DO

        R(DO) = Ka*(DO_sat - DO) - kd*BOD - SOD/h

        Parameters:
        -----------
        DO : array
            DO (mg/L)
        BOD : array
            BOD (mg/L)
        u : array
             (m/s)
        h : array
             (m)
        T : array
             (°C)
        ice_cover_fraction : array, optional
             (0-1)

        Returns:
        --------
        R_DO : array
            DO (mg/L/day)
        """
        # 1. 
        DO_sat = self.compute_DO_saturation(T)
        Ka = self.compute_reaeration_coefficient(u, h, T, ice_cover_fraction)
        reaeration = Ka * (DO_sat - DO)

        # 2. BOD
        bod_consumption = -self.compute_BOD_decay(BOD, T)

        # 3. 
        sod_consumption = -self.compute_sediment_oxygen_demand(h, T)

        # 
        R_DO = reaeration + bod_consumption + sod_consumption

        return R_DO

    def compute_BOD_reaction(
        self,
        BOD: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        BOD

        R(BOD) = -kd*BOD

        Parameters:
        -----------
        BOD : array
            BOD (mg/L)
        T : array
             (°C)

        Returns:
        --------
        R_BOD : array
            BOD (mg/L/day)
        """
        R_BOD = -self.compute_BOD_decay(BOD, T)
        return R_BOD

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        manning_n: float = 0.03,
        ice_cover_fraction: Optional[np.ndarray] = None,
        BOD_source: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
         (DOBOD)

        Strang Splitting:
        1. 
        2. 
        3. 

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
        manning_n : float
            Manning
        ice_cover_fraction : array, optional
             (0-1)
        BOD_source : array, optional
            BOD (mg/L/day)

        Returns:
        --------
        state : dict
            {'DO': array, 'BOD': array}
        """
        # 
        D_L = self.compute_dispersion_coefficient(h, u, manning_n=manning_n)

        #  s -> day
        dt_day = dt / 86400.0

        # ========== Step 1:  ==========
        # DO
        R_DO = self.compute_reaction_terms(
            self.DO, self.BOD, u, h, T, ice_cover_fraction
        )
        self.DO += 0.5 * dt_day * R_DO
        self.DO = np.maximum(self.DO, 0.0)

        # BOD
        R_BOD = self.compute_BOD_reaction(self.BOD, T)
        if BOD_source is not None:
            R_BOD += BOD_source
        self.BOD += 0.5 * dt_day * R_BOD
        self.BOD = np.maximum(self.BOD, 0.0)

        # ========== Step 2:  ==========
        self.DO = self.solve_transport(dt, self.DO, u, h, D_L)
        self.BOD = self.solve_transport(dt, self.BOD, u, h, D_L)

        # ========== Step 3:  ==========
        # DO
        R_DO = self.compute_reaction_terms(
            self.DO, self.BOD, u, h, T, ice_cover_fraction
        )
        self.DO += 0.5 * dt_day * R_DO
        self.DO = np.maximum(self.DO, 0.0)

        # BOD
        R_BOD = self.compute_BOD_reaction(self.BOD, T)
        if BOD_source is not None:
            R_BOD += BOD_source
        self.BOD += 0.5 * dt_day * R_BOD
        self.BOD = np.maximum(self.BOD, 0.0)

        return self.get_state()

    def get_state(self) -> Dict[str, np.ndarray]:
        """"""
        return {
            'DO': self.DO.copy(),
            'BOD': self.BOD.copy()
        }

    def get_diagnostics(
        self,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        

        Returns:
        --------
        diag : dict
            
        """
        DO_sat = self.compute_DO_saturation(T)
        Ka = self.compute_reaeration_coefficient(u, h, T, ice_cover_fraction)
        kd_T = self.kd_20 * self.theta_kd**(T - 20)
        SOD_rate = self.compute_sediment_oxygen_demand(h, T)

        diag = {
            'DO_saturation': DO_sat,
            'DO_deficit': DO_sat - self.DO,
            'saturation_percent': 100 * self.DO / (DO_sat + 1e-12),
            'reaeration_coeff': Ka,
            'reaeration_rate': Ka * (DO_sat - self.DO),
            'BOD_decay_coeff': kd_T,
            'BOD_consumption': -kd_T * self.BOD,
            'SOD_rate': -SOD_rate
        }

        return diag


class StreeterPhelpsAnalytical:
    """
    Streeter-Phelps (DO)

    DO:
        DO_deficit(x) = (kd*L0)/(ka-kd) * (exp(-kd*t) - exp(-ka*t)) + D0*exp(-ka*t)

    :
        - L0: BOD
        - D0: DO
        - t = x/u ()
    """

    def __init__(
        self,
        ka: float,  #  (1/day)
        kd: float,  # BOD (1/day)
        u: float    #  (m/s)
    ):
        self.ka = ka
        self.kd = kd
        self.u = u

    def compute_deficit(
        self,
        x: np.ndarray,
        DO_sat: float,
        DO_0: float,
        BOD_0: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        DODO

        Parameters:
        -----------
        x : array
             (m)
        DO_sat : float
            DO (mg/L)
        DO_0 : float
            DO (mg/L)
        BOD_0 : float
            BOD (mg/L)

        Returns:
        --------
        DO : array
            DO (mg/L)
        deficit : array
            DO (mg/L)
        """
        #  (day)
        t = x / self.u / 86400.0

        # 
        D0 = DO_sat - DO_0

        # Streeter-Phelps
        if abs(self.ka - self.kd) > 1e-6:
            deficit = (
                (self.kd * BOD_0) / (self.ka - self.kd)
                * (np.exp(-self.kd * t) - np.exp(-self.ka * t))
                + D0 * np.exp(-self.ka * t)
            )
        else:
            # ka ≈ kd
            deficit = (self.kd * BOD_0 * t * np.exp(-self.ka * t)
                       + D0 * np.exp(-self.ka * t))

        DO = DO_sat - deficit

        return DO, deficit

    def find_critical_point(
        self,
        DO_sat: float,
        DO_0: float,
        BOD_0: float
    ) -> Tuple[float, float]:
        """
         (DO)

        tc = 1/(ka-kd) * ln[(ka/kd) * (1 - D0*(ka-kd)/(kd*BOD_0))]

        Returns:
        --------
        x_critical : float
             (m)
        DO_critical : float
            DO (mg/L)
        """
        D0 = DO_sat - DO_0

        if abs(self.ka - self.kd) > 1e-6:
            term = (self.ka / self.kd) * (1 - D0 * (self.ka - self.kd) / (self.kd * BOD_0))
            if term > 0:
                t_critical = np.log(term) / (self.ka - self.kd)
            else:
                t_critical = 0
        else:
            t_critical = D0 / (self.kd * BOD_0)

        x_critical = t_critical * self.u * 86400.0  # m

        # DO
        deficit_critical = (
            (self.kd * BOD_0) / (self.ka - self.kd)
            * (np.exp(-self.kd * t_critical) - np.exp(-self.ka * t_critical))
            + D0 * np.exp(-self.ka * t_critical)
        )
        DO_critical = DO_sat - deficit_critical

        return x_critical, DO_critical
