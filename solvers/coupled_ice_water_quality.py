#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
- (Coupled Ice-Water Quality Solver)

HydroClaude:
- Phase 1: DO
- Phase 2: 
- Phase 3:  ()
- Phase 4: 

:
- 
- 
- 
- 

: MIKE ICE + WASP + CE-QUAL-W2 

: HydroClaude Team
: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple
import time

# 
from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver


class CoupledIceWaterQualitySolver:
    """
    -

    :
    -  (WaterTemperatureSolver)
    - DO (DissolvedOxygenSolver)
    -  (IceCoverSolver)
    -  (NutrientsSolver)
    -  (PhytoplanktonSolver)

    :
    -  → DO
    -  → DO
    - DO ↔  ()
    - DO ↔  ()
    -  →  ()
    -  →  ()
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        # 
        enable_temperature: bool = True,
        # DO
        enable_do: bool = True,
        BOD_decay_rate: float = 0.2,
        SOD_rate: float = 1.0,
        # 
        enable_ice: bool = True,
        # 
        enable_nutrients: bool = True,
        kn_20: float = 0.1,
        kdn_20: float = 0.09,
        # 
        enable_phytoplankton: bool = True,
        mu_max_20: float = 2.0,
        # 
        use_numba: bool = True,
        # 
        adaptive_dt: bool = True,
        dt_min: float = 60.0,      #  (s)
        dt_max: float = 3600.0,    #  (s)
        CFL: float = 0.5           # CFL
    ):
        """
        

        Parameters:
        -----------
        n_cells : int
            
        dx : float
             (m)
        enable_temperature : bool
            
        enable_do : bool
            DO
        enable_ice : bool
            
        enable_nutrients : bool
            
        enable_phytoplankton : bool
            
        use_numba : bool
            Numba
        adaptive_dt : bool
            
        dt_min, dt_max : float
             (s)
        CFL : float
            CFL ()
        """
        self.n_cells = n_cells
        self.dx = dx

        # 
        self.enable_temperature = enable_temperature
        self.enable_do = enable_do
        self.enable_ice = enable_ice
        self.enable_nutrients = enable_nutrients
        self.enable_phytoplankton = enable_phytoplankton

        # 
        self.adaptive_dt = adaptive_dt
        self.dt_min = dt_min
        self.dt_max = dt_max
        self.CFL = CFL

        # 
        if self.enable_temperature:
            self.temp_solver = WaterTemperatureSolver(
                n_cells, dx, use_numba=use_numba
            )

        if self.enable_do:
            self.do_solver = DissolvedOxygenSolver(
                n_cells, dx,
                kd_20=BOD_decay_rate,
                SOD_20=SOD_rate,
                use_numba=use_numba
            )

        if self.enable_ice:
            self.ice_solver = IceCoverSolver(
                n_cells=n_cells
            )

        if self.enable_nutrients:
            self.nutrients_solver = NutrientsSolver(
                n_cells, dx,
                kn_20=kn_20,
                kdn_20=kdn_20,
                use_numba=use_numba
            )

        if self.enable_phytoplankton:
            self.algae_solver = PhytoplanktonSolver(
                n_cells, dx,
                mu_max_20=mu_max_20,
                use_numba=use_numba
            )

        # 
        self.total_steps = 0
        self.total_time = 0.0
        self.wallclock_time = 0.0

    def initialize(
        self,
        # 
        h: np.ndarray,
        u: np.ndarray,
        # 
        T_initial: Optional[np.ndarray] = None,
        # DO
        DO_initial: Optional[np.ndarray] = None,
        BOD_initial: Optional[np.ndarray] = None,
        # 
        h_ice_initial: Optional[np.ndarray] = None,
        # 
        NH4_initial: Optional[np.ndarray] = None,
        NO3_initial: Optional[np.ndarray] = None,
        OrgN_initial: Optional[np.ndarray] = None,
        PO4_initial: Optional[np.ndarray] = None,
        OrgP_initial: Optional[np.ndarray] = None,
        # 
        Chla_initial: Optional[np.ndarray] = None
    ):
        """
        

        Parameters:
        -----------
        h : array
             (m)
        u : array
             (m/s)
        T_initial : array, optional
             (°C)
        DO_initial : array, optional
            DO (mg/L)
        BOD_initial : array, optional
            BOD (mg/L)
        h_ice_initial : array, optional
             (m)
        NH4_initial, NO3_initial, OrgN_initial : array, optional
             (mg/L)
        PO4_initial, OrgP_initial : array, optional
             (mg/L)
        Chla_initial : array, optional
             (μg/L)
        """
        # 
        self.h = h.copy()
        self.u = u.copy()

        # 
        if self.enable_temperature:
            if T_initial is None:
                T_initial = np.full(self.n_cells, 10.0)
            self.temp_solver.initialize(T_initial)

        # DO
        if self.enable_do:
            if DO_initial is None:
                DO_initial = np.full(self.n_cells, 8.0)
            if BOD_initial is None:
                BOD_initial = np.full(self.n_cells, 2.0)
            self.do_solver.initialize(DO_initial, BOD_initial)

        # 
        if self.enable_ice:
            if h_ice_initial is None:
                h_ice_initial = np.zeros(self.n_cells)
            self.ice_solver.h_ice = h_ice_initial.copy()

        # 
        if self.enable_nutrients:
            if NH4_initial is None:
                NH4_initial = np.full(self.n_cells, 0.5)
            if NO3_initial is None:
                NO3_initial = np.full(self.n_cells, 2.0)
            if OrgN_initial is None:
                OrgN_initial = np.full(self.n_cells, 1.0)
            if PO4_initial is None:
                PO4_initial = np.full(self.n_cells, 0.1)
            if OrgP_initial is None:
                OrgP_initial = np.full(self.n_cells, 0.05)

            self.nutrients_solver.initialize(
                NH4_initial, NO3_initial, OrgN_initial,
                PO4_initial, OrgP_initial
            )

        # 
        if self.enable_phytoplankton:
            if Chla_initial is None:
                Chla_initial = np.full(self.n_cells, 10.0)
            self.algae_solver.initialize(Chla_initial)

    def compute_adaptive_timestep(
        self,
        u: np.ndarray,
        h: np.ndarray
    ) -> float:
        """
        

        CFL:
        dt = CFL * dx / max(|u|)

        Parameters:
        -----------
        u : array
             (m/s)
        h : array
             (m)

        Returns:
        --------
        dt : float
             (s)
        """
        if not self.adaptive_dt:
            return self.dt_max

        # CFL
        u_max = np.max(np.abs(u)) + 1e-10
        dt_cfl = self.CFL * self.dx / u_max

        # 
        dt = np.clip(dt_cfl, self.dt_min, self.dt_max)

        return dt

    def step(
        self,
        dt: float,
        # 
        u: np.ndarray,
        h: np.ndarray,
        manning_n: np.ndarray,
        # 
        T_air: float,
        solar_radiation: float,
        wind_speed: float,
        relative_humidity: float,
        cloud_cover: float = 0.0,
        #  ()
        I_0: Optional[np.ndarray] = None
    ) -> Dict:
        """
         ()

        Parameters:
        -----------
        dt : float
             (s)
        u : array
             (m/s)
        h : array
             (m)
        manning_n : array
            
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
        I_0 : array, optional
             (W/m²), solar_radiation

        Returns:
        --------
        state : dict
            
        """
        t_start = time.time()

        # 
        if self.adaptive_dt:
            dt_adaptive = self.compute_adaptive_timestep(u, h)
            dt = min(dt, dt_adaptive)

        # 
        if I_0 is None:
            I_0 = np.full(self.n_cells, solar_radiation)

        # ====================================
        # Step 1: 
        # ====================================
        if self.enable_temperature:
            #  ()
            if self.enable_ice:
                ice_cover_fraction = np.where(self.ice_solver.h_ice > 0.01, 1.0, 0.0)
            else:
                ice_cover_fraction = np.zeros(self.n_cells)

            ice_thickness = self.ice_solver.h_ice if self.enable_ice else None
            T = self.temp_solver.step(
                dt, u, h,
                T_air, solar_radiation, wind_speed, relative_humidity,
                ice_cover_thickness=ice_thickness,
                ice_cover_fraction=ice_cover_fraction
            )
        else:
            T = np.full(self.n_cells, 10.0)  # 

        # ====================================
        # Step 2: 
        # ====================================
        if self.enable_ice:
            state_ice = self.ice_solver.step(dt, T_air, T)
            h_ice = state_ice['h_ice']
            ice_cover_fraction = np.where(h_ice > 0.01, 1.0, 0.0)
        else:
            h_ice = np.zeros(self.n_cells)
            ice_cover_fraction = np.zeros(self.n_cells)

        # ====================================
        # Step 3: 
        # ====================================
        if self.enable_nutrients:
            # DO (/)
            if self.enable_do:
                DO = self.do_solver.DO.copy()
            else:
                DO = np.full(self.n_cells, 8.0)

            state_nutrients = self.nutrients_solver.step(dt, u, h, T, DO)

            NH4 = state_nutrients['NH4']
            NO3 = state_nutrients['NO3']
            PO4 = state_nutrients['PO4']
        else:
            NH4 = np.full(self.n_cells, 0.5)
            NO3 = np.full(self.n_cells, 2.0)
            PO4 = np.full(self.n_cells, 0.1)

        # ====================================
        # Step 4: 
        # ====================================
        if self.enable_phytoplankton:
            state_algae = self.algae_solver.step(
                dt, u, h, T, I_0, NH4, NO3, PO4, ice_cover_fraction
            )

            Chla = state_algae['Chla']
            algae_O2_production = state_algae['DO_production']
            algae_NH4_uptake = state_algae['NH4_uptake']
            algae_NO3_uptake = state_algae['NO3_uptake']
            algae_PO4_uptake = state_algae['PO4_uptake']
        else:
            Chla = np.full(self.n_cells, 10.0)
            algae_O2_production = np.zeros(self.n_cells)
            algae_NH4_uptake = np.zeros(self.n_cells)
            algae_NO3_uptake = np.zeros(self.n_cells)
            algae_PO4_uptake = np.zeros(self.n_cells)

        # ====================================
        # Step 5: DO ()
        # ====================================
        if self.enable_do:
            #  ()
            if self.enable_nutrients:
                nitrif_rate, nitrif_O2 = self.nutrients_solver.compute_nitrification_rate(NH4, DO, T)
                nitrification_O2_demand = nitrif_O2
            else:
                nitrification_O2_demand = np.zeros(self.n_cells)

            # DO
            state_do = self.do_solver.step(
                dt, u, h, T, manning_n, ice_cover_fraction
            )

            # DO
            # (+) - (-)
            dt_day = dt / 86400.0
            DO_change = (algae_O2_production - nitrification_O2_demand) * dt_day
            self.do_solver.DO += DO_change
            self.do_solver.DO = np.maximum(self.do_solver.DO, 0.0)

            DO = self.do_solver.DO.copy()
            BOD = self.do_solver.BOD.copy()
        else:
            DO = np.full(self.n_cells, 8.0)
            BOD = np.full(self.n_cells, 2.0)
            nitrification_O2_demand = np.zeros(self.n_cells)

        # ====================================
        # Step 6: -
        # ====================================
        if self.enable_nutrients and self.enable_phytoplankton:
            #  ()
            # 
            # 
            dt_day = dt / 86400.0
            self.nutrients_solver.NH4 -= algae_NH4_uptake * dt_day
            self.nutrients_solver.NO3 -= algae_NO3_uptake * dt_day
            self.nutrients_solver.PO4 -= algae_PO4_uptake * dt_day

            # 
            self.nutrients_solver.NH4 = np.maximum(self.nutrients_solver.NH4, 0.0)
            self.nutrients_solver.NO3 = np.maximum(self.nutrients_solver.NO3, 0.0)
            self.nutrients_solver.PO4 = np.maximum(self.nutrients_solver.PO4, 0.0)

        # ====================================
        # 
        # ====================================
        self.total_steps += 1
        self.total_time += dt
        self.wallclock_time += (time.time() - t_start)

        # ====================================
        # 
        # ====================================
        state = {
            # 
            'h': h.copy(),
            'u': u.copy(),
            # 
            'T': T.copy(),
            # 
            'h_ice': h_ice.copy(),
            'ice_cover_fraction': ice_cover_fraction.copy(),
            # DO
            'DO': DO.copy(),
            'BOD': BOD.copy(),
            # 
            'NH4': self.nutrients_solver.NH4.copy() if self.enable_nutrients else NH4,
            'NO3': self.nutrients_solver.NO3.copy() if self.enable_nutrients else NO3,
            'OrgN': self.nutrients_solver.OrgN.copy() if self.enable_nutrients else np.zeros(self.n_cells),
            'PO4': self.nutrients_solver.PO4.copy() if self.enable_nutrients else PO4,
            'OrgP': self.nutrients_solver.OrgP.copy() if self.enable_nutrients else np.zeros(self.n_cells),
            'TN': (NH4 + NO3 + self.nutrients_solver.OrgN) if self.enable_nutrients else (NH4 + NO3),
            'TP': (PO4 + self.nutrients_solver.OrgP) if self.enable_nutrients else PO4,
            # 
            'Chla': Chla.copy(),
            # 
            'algae_O2_production': algae_O2_production,
            'nitrification_O2_demand': nitrification_O2_demand if self.enable_nutrients else np.zeros(self.n_cells),
            # 
            'dt': dt,
            'time': self.total_time
        }

        return state

    def get_performance_stats(self) -> Dict:
        """
        

        Returns:
        --------
        stats : dict
            
        """
        if self.total_steps > 0:
            avg_wallclock_per_step = self.wallclock_time / self.total_steps
            speedup_factor = self.total_time / (self.wallclock_time + 1e-10)
        else:
            avg_wallclock_per_step = 0.0
            speedup_factor = 0.0

        stats = {
            'total_steps': self.total_steps,
            'total_simulated_time': self.total_time,
            'total_wallclock_time': self.wallclock_time,
            'avg_wallclock_per_step': avg_wallclock_per_step,
            'speedup_factor': speedup_factor
        }

        return stats
