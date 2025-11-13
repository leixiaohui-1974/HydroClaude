#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 - Nutrients Cycling Model


    :
    ∂NH4/∂t + u·∂NH4/∂x = DL·∂²NH4/∂x² - kn·NH4·θ(DO) + km1·OrgN - vs1·NH4/h
    ∂NO3/∂t + u·∂NO3/∂x = DL·∂²NO3/∂x² + kn·NH4·θ(DO) - kdn·NO3·(1-θ(DO))
    ∂OrgN/∂t + u·∂OrgN/∂x = DL·∂²OrgN/∂x² - km1·OrgN - vs2·OrgN/h

    :
    ∂PO4/∂t + u·∂PO4/∂x = DL·∂²PO4/∂x² + km2·OrgP - vs3·PO4/h + Prelease
    ∂OrgP/∂t + u·∂OrgP/∂x = DL·∂²OrgP/∂x² - km2·OrgP - vs4·OrgP/h

:
    - kn:  (1/day)
    - kdn:  (1/day)
    - km:  (1/day)
    - vs:  (m/day)
    - θ(DO): DO (Monod)
    - Prelease:  (mg/L/day)

: WASP, CE-QUAL-W2

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple
from .water_quality_adr import ADRSolver


class NutrientsSolver(ADRSolver):
    """
    

    
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        # 
        kn_20: float = 0.1,      #  @ 20°C (1/day)
        kdn_20: float = 0.09,    #  @ 20°C (1/day)
        km_N_20: float = 0.075,  #  @ 20°C (1/day)
        vs_NH4: float = 0.0,     # NH4 (m/day) - 
        vs_OrgN: float = 0.1,    #  (m/day)
        # 
        km_P_20: float = 0.075,  #  @ 20°C (1/day)
        vs_PO4: float = 0.0,     # PO4 (m/day) - 
        vs_OrgP: float = 0.1,    #  (m/day)
        P_release_20: float = 5.0,  #  @ 20°C (mg/m²/day)
        # 
        use_numba: bool = True
    ):
        """
        

        Parameters:
        -----------
        n_cells : int
            
        dx : float
             (m)
        kn_20 : float
             @ 20°C (1/day)
        kdn_20 : float
             @ 20°C (1/day)
        km_N_20 : float
             @ 20°C (1/day)
        vs_NH4 : float
            NH4 (m/day)
        vs_OrgN : float
             (m/day)
        km_P_20 : float
             @ 20°C (1/day)
        vs_PO4 : float
            PO4 (m/day)
        vs_OrgP : float
             (m/day)
        P_release_20 : float
             @ 20°C (mg/m²/day)
        use_numba : bool
            Numba
        """
        super().__init__(n_cells, dx, use_numba=use_numba, use_muscl=True)

        # 
        self.NH4 = np.ones(n_cells) * 0.5   #  (mg/L)
        self.NO3 = np.ones(n_cells) * 2.0   #  (mg/L)
        self.OrgN = np.ones(n_cells) * 1.0  #  (mg/L)
        self.PO4 = np.ones(n_cells) * 0.1   #  (mg/L)
        self.OrgP = np.ones(n_cells) * 0.05 #  (mg/L)

        # 
        self.kn_20 = kn_20
        self.kdn_20 = kdn_20
        self.km_N_20 = km_N_20
        self.vs_NH4 = vs_NH4
        self.vs_OrgN = vs_OrgN

        # 
        self.km_P_20 = km_P_20
        self.vs_PO4 = vs_PO4
        self.vs_OrgP = vs_OrgP
        self.P_release_20 = P_release_20

        # 
        self.theta_kn = 1.08    # 
        self.theta_kdn = 1.045  # 
        self.theta_km = 1.047   # 
        self.theta_P_release = 1.08  # 

        # Monod
        self.K_DO_nitrif = 0.5  # DO (mg/L)
        self.K_DO_denitrif = 0.5  # DO (mg/L)

        # DO-
        self.O2_per_NH4 = 4.57  #  (mg O2 / mg NH4-N)

    def initialize(
        self,
        NH4_initial: np.ndarray,
        NO3_initial: np.ndarray,
        OrgN_initial: Optional[np.ndarray] = None,
        PO4_initial: Optional[np.ndarray] = None,
        OrgP_initial: Optional[np.ndarray] = None
    ):
        """
        

        Parameters:
        -----------
        NH4_initial : array
            NH4 (mg/L)
        NO3_initial : array
            NO3 (mg/L)
        OrgN_initial : array, optional
             (mg/L)
        PO4_initial : array, optional
            PO4 (mg/L)
        OrgP_initial : array, optional
             (mg/L)
        """
        self.NH4 = NH4_initial.copy()
        self.NO3 = NO3_initial.copy()

        if OrgN_initial is not None:
            self.OrgN = OrgN_initial.copy()

        if PO4_initial is not None:
            self.PO4 = PO4_initial.copy()

        if OrgP_initial is not None:
            self.OrgP = OrgP_initial.copy()

    def compute_nitrification_rate(
        self,
        NH4: np.ndarray,
        DO: np.ndarray,
        T: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        NH4 + 2O2 → NO3 + H2O + 2H+

        Parameters:
        -----------
        NH4 : array
             (mg/L)
        DO : array
             (mg/L)
        T : array
             (°C)

        Returns:
        --------
        nitrif_rate : array
             (mg/L/day)
        DO_consumption : array
             (mg/L/day)
        """
        # 
        kn_T = self.kn_20 * self.theta_kn**(T - 20)

        # DO (Monod)
        DO_factor = DO / (DO + self.K_DO_nitrif)

        # 
        nitrif_rate = kn_T * NH4 * DO_factor

        # 
        DO_consumption = self.O2_per_NH4 * nitrif_rate

        return nitrif_rate, DO_consumption

    def compute_denitrification_rate(
        self,
        NO3: np.ndarray,
        DO: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        

        NO3 → N2 ()

        Parameters:
        -----------
        NO3 : array
             (mg/L)
        DO : array
             (mg/L)
        T : array
             (°C)

        Returns:
        --------
        denitrif_rate : array
             (mg/L/day)
        """
        # 
        kdn_T = self.kdn_20 * self.theta_kdn**(T - 20)

        # DO ()
        # DO
        DO_inhibition = np.maximum(0, (self.K_DO_denitrif - DO)) / self.K_DO_denitrif

        # 
        denitrif_rate = kdn_T * NO3 * DO_inhibition

        return denitrif_rate

    def compute_organic_N_mineralization(
        self,
        OrgN: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        

        OrgN → NH4

        Parameters:
        -----------
        OrgN : array
             (mg/L)
        T : array
             (°C)

        Returns:
        --------
        mineral_rate : array
             (mg/L/day)
        """
        # 
        km_T = self.km_N_20 * self.theta_km**(T - 20)

        # 
        mineral_rate = km_T * OrgN

        return mineral_rate

    def compute_settling_N(
        self,
        NH4: np.ndarray,
        OrgN: np.ndarray,
        h: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        Parameters:
        -----------
        NH4 : array
             (mg/L)
        OrgN : array
             (mg/L)
        h : array
             (m)

        Returns:
        --------
        settling_NH4 : array
            NH4 (mg/L/day)
        settling_OrgN : array
             (mg/L/day)
        """
        # NH4 ()
        settling_NH4 = -self.vs_NH4 * NH4 / h

        #  ()
        settling_OrgN = -self.vs_OrgN * OrgN / h

        return settling_NH4, settling_OrgN

    def compute_organic_P_mineralization(
        self,
        OrgP: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        

        OrgP → PO4

        Parameters:
        -----------
        OrgP : array
             (mg/L)
        T : array
             (°C)

        Returns:
        --------
        mineral_rate : array
             (mg/L/day)
        """
        # 
        km_T = self.km_P_20 * self.theta_km**(T - 20)

        # 
        mineral_rate = km_T * OrgP

        return mineral_rate

    def compute_P_sediment_release(
        self,
        DO: np.ndarray,
        T: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        

        

        Parameters:
        -----------
        DO : array
             (mg/L)
        T : array
             (°C)
        h : array
             (m)

        Returns:
        --------
        release_rate : array
             (mg/L/day)
        """
        # 
        P_release_T = self.P_release_20 * self.theta_P_release**(T - 20)

        # DO ()
        DO_factor = np.ones_like(DO)
        mask_anaerobic = DO < 1.0
        DO_factor[mask_anaerobic] = (1.0 - DO[mask_anaerobic])

        #  (mg/m²/day -> mg/L/day)
        release_rate = P_release_T * DO_factor / h  # mg/m²/day / m = mg/L/day

        return release_rate

    def compute_settling_P(
        self,
        PO4: np.ndarray,
        OrgP: np.ndarray,
        h: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        Parameters:
        -----------
        PO4 : array
             (mg/L)
        OrgP : array
             (mg/L)
        h : array
             (m)

        Returns:
        --------
        settling_PO4 : array
            PO4 (mg/L/day)
        settling_OrgP : array
             (mg/L/day)
        """
        # PO4 ()
        settling_PO4 = -self.vs_PO4 * PO4 / h

        #  ()
        settling_OrgP = -self.vs_OrgP * OrgP / h

        return settling_PO4, settling_OrgP

    def compute_nitrogen_reactions(
        self,
        NH4: np.ndarray,
        NO3: np.ndarray,
        OrgN: np.ndarray,
        DO: np.ndarray,
        T: np.ndarray,
        h: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        

        Parameters:
        -----------
        NH4, NO3, OrgN : array
             (mg/L)
        DO : array
             (mg/L)
        T : array
             (°C)
        h : array
             (m)

        Returns:
        --------
        R_NH4, R_NO3, R_OrgN : array
             (mg/L/day)
        DO_consumption : array
             (mg/L/day)
        """
        # 
        nitrif_rate, DO_nitrif = self.compute_nitrification_rate(NH4, DO, T)

        # 
        denitrif_rate = self.compute_denitrification_rate(NO3, DO, T)

        # 
        mineral_N_rate = self.compute_organic_N_mineralization(OrgN, T)

        # 
        settling_NH4, settling_OrgN = self.compute_settling_N(NH4, OrgN, h)

        # 
        R_NH4 = -nitrif_rate + mineral_N_rate + settling_NH4
        R_NO3 = nitrif_rate - denitrif_rate
        R_OrgN = -mineral_N_rate + settling_OrgN

        return R_NH4, R_NO3, R_OrgN, DO_nitrif

    def compute_phosphorus_reactions(
        self,
        PO4: np.ndarray,
        OrgP: np.ndarray,
        DO: np.ndarray,
        T: np.ndarray,
        h: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        Parameters:
        -----------
        PO4, OrgP : array
             (mg/L)
        DO : array
             (mg/L)
        T : array
             (°C)
        h : array
             (m)

        Returns:
        --------
        R_PO4, R_OrgP : array
             (mg/L/day)
        """
        # 
        mineral_P_rate = self.compute_organic_P_mineralization(OrgP, T)

        # 
        release_rate = self.compute_P_sediment_release(DO, T, h)

        # 
        settling_PO4, settling_OrgP = self.compute_settling_P(PO4, OrgP, h)

        # 
        R_PO4 = mineral_P_rate + release_rate + settling_PO4
        R_OrgP = -mineral_P_rate + settling_OrgP

        return R_PO4, R_OrgP

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        DO: np.ndarray,
        manning_n: float = 0.03
    ) -> Dict[str, np.ndarray]:
        """
        

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
        DO : array
             (mg/L)
        manning_n : float
            Manning

        Returns:
        --------
        state : dict
             + DO
        """
        # 
        D_L = self.compute_dispersion_coefficient(h, u, manning_n=manning_n)

        #  s -> day
        dt_day = dt / 86400.0

        # ========== Step 1:  ==========
        # 
        R_NH4, R_NO3, R_OrgN, DO_nitrif = self.compute_nitrogen_reactions(
            self.NH4, self.NO3, self.OrgN, DO, T, h
        )

        self.NH4 += 0.5 * dt_day * R_NH4
        self.NO3 += 0.5 * dt_day * R_NO3
        self.OrgN += 0.5 * dt_day * R_OrgN

        # 
        R_PO4, R_OrgP = self.compute_phosphorus_reactions(
            self.PO4, self.OrgP, DO, T, h
        )

        self.PO4 += 0.5 * dt_day * R_PO4
        self.OrgP += 0.5 * dt_day * R_OrgP

        # 
        self.NH4 = np.maximum(self.NH4, 0.0)
        self.NO3 = np.maximum(self.NO3, 0.0)
        self.OrgN = np.maximum(self.OrgN, 0.0)
        self.PO4 = np.maximum(self.PO4, 0.0)
        self.OrgP = np.maximum(self.OrgP, 0.0)

        # ========== Step 2:  ==========
        self.NH4 = self.solve_transport(dt, self.NH4, u, h, D_L)
        self.NO3 = self.solve_transport(dt, self.NO3, u, h, D_L)
        self.OrgN = self.solve_transport(dt, self.OrgN, u, h, D_L)
        self.PO4 = self.solve_transport(dt, self.PO4, u, h, D_L)
        self.OrgP = self.solve_transport(dt, self.OrgP, u, h, D_L)

        # ========== Step 3:  ==========
        # 
        R_NH4, R_NO3, R_OrgN, DO_nitrif = self.compute_nitrogen_reactions(
            self.NH4, self.NO3, self.OrgN, DO, T, h
        )

        self.NH4 += 0.5 * dt_day * R_NH4
        self.NO3 += 0.5 * dt_day * R_NO3
        self.OrgN += 0.5 * dt_day * R_OrgN

        # 
        R_PO4, R_OrgP = self.compute_phosphorus_reactions(
            self.PO4, self.OrgP, DO, T, h
        )

        self.PO4 += 0.5 * dt_day * R_PO4
        self.OrgP += 0.5 * dt_day * R_OrgP

        # 
        self.NH4 = np.maximum(self.NH4, 0.0)
        self.NO3 = np.maximum(self.NO3, 0.0)
        self.OrgN = np.maximum(self.OrgN, 0.0)
        self.PO4 = np.maximum(self.PO4, 0.0)
        self.OrgP = np.maximum(self.OrgP, 0.0)

        return self.get_state(DO_nitrif)

    def get_state(self, DO_consumption: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """"""
        state = {
            'NH4': self.NH4.copy(),
            'NO3': self.NO3.copy(),
            'OrgN': self.OrgN.copy(),
            'PO4': self.PO4.copy(),
            'OrgP': self.OrgP.copy(),
            'TN': self.NH4 + self.NO3 + self.OrgN,  # 
            'TP': self.PO4 + self.OrgP,             # 
            'N_P_ratio': (self.NH4 + self.NO3 + self.OrgN) / (self.PO4 + self.OrgP + 1e-12)
        }

        if DO_consumption is not None:
            state['DO_nitrification'] = DO_consumption

        return state

    def get_diagnostics(
        self,
        DO: np.ndarray,
        T: np.ndarray,
        h: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        

        Returns:
        --------
        diag : dict
            
        """
        # 
        nitrif_rate, DO_nitrif = self.compute_nitrification_rate(self.NH4, DO, T)
        denitrif_rate = self.compute_denitrification_rate(self.NO3, DO, T)
        mineral_N_rate = self.compute_organic_N_mineralization(self.OrgN, T)
        mineral_P_rate = self.compute_organic_P_mineralization(self.OrgP, T)
        P_release = self.compute_P_sediment_release(DO, T, h)

        diag = {
            'nitrification_rate': nitrif_rate,
            'denitrification_rate': denitrif_rate,
            'N_mineralization_rate': mineral_N_rate,
            'P_mineralization_rate': mineral_P_rate,
            'P_sediment_release': P_release,
            'DO_nitrification': DO_nitrif,
            'TN': self.NH4 + self.NO3 + self.OrgN,
            'TP': self.PO4 + self.OrgP,
            'inorganic_N': self.NH4 + self.NO3,
            'N_P_ratio': (self.NH4 + self.NO3 + self.OrgN) / (self.PO4 + self.OrgP + 1e-12)
        }

        return diag
