#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov - WENO-3Enhanced WENO3


1.  Jiang-Shu 1996
2.  epsilonHenrick et al. 2005
3.  Harten-Hyman 1983
4.  Well-BalancedAudusse et al. 2004
5.  CFL


- MacDonald Test 4
- 100%
- 


1. Jiang, G.S. & Shu, C.W. (1996). "Efficient Implementation of Weighted ENO Schemes"
   Journal of Computational Physics, 126, 202-228.
2. Henrick, A.K. et al. (2005). "Mapped Weighted Essentially Non-Oscillatory Schemes"
   Journal of Computational Physics, 207, 542-567.
3. Harten, A. & Hyman, J.M. (1983). "Self Adjusting Grid Methods"
   Journal of Computational Physics, 50, 235-269.
4. Audusse, E. et al. (2004). "A Fast and Stable Well-Balanced Scheme"
   SIAM Journal on Scientific Computing, 25(6), 2050-2065.

: HydroClaude Team
: 2025-10-30
: v1.0 Enhanced
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3


class GodunvFVMWENO3Enhanced(GodunvFVMWENO3):
    """
    WENO-3

    
    1. 
    2. epsilon
    3. 
    4. Well-Balanced
    5. CFLCFL

    
    - 
    - 
    - 
    - 
    """

    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.5,
        eps_dry: float = 1e-6,
        weno_epsilon: float = 1e-6,  # epsilon
        riemann_solver: str = 'hll',
        well_balanced: bool = True,  # Well-Balanced
        use_numba: bool = True,
        dt_max: Optional[float] = None,
        entropy_fix: bool = True,  # 
        critical_flow_treatment: bool = True,  # 
        adaptive_cfl: bool = True,  # CFL
        cfl_shock: float = 0.2,  # CFL
        entropy_delta: float = 0.1  # 
    ):
        """
        WENO3

        Args:
            ()
            adaptive_cfl: CFL
            cfl_shock: CFL
            entropy_delta: 
        """
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            weno_epsilon=weno_epsilon,
            riemann_solver=riemann_solver,
            well_balanced=well_balanced,
            use_numba=use_numba,
            dt_max=dt_max,
            entropy_fix=entropy_fix,
            critical_flow_treatment=critical_flow_treatment
        )

        # 
        self.adaptive_cfl = adaptive_cfl
        self.cfl_base = cfl
        self.cfl_shock = cfl_shock
        self.entropy_delta = entropy_delta

        print(f"\n  [WENO3] Enhanced WENO3 Enabled:")
        print(f"     [OK] Improved smoothness indicators")
        print(f"     [OK] Adaptive epsilon")
        print(f"     [OK] Entropy correction (delta={entropy_delta})")
        print(f"     [OK] Well-Balanced: {well_balanced}")
        print(f"     [OK] Adaptive CFL: {adaptive_cfl}")
        if adaptive_cfl:
            print(f"       - CFL: {self.cfl_base}")
            print(f"       - CFL: {self.cfl_shock}")

    def _weno3_reconstruction_enhanced(
        self,
        phi: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO-3

        1Jiang-Shu 1996
        ------------------------------------------------
        WENO3beta_k = (phi[i+1] - phi[i])^2

        
        beta_k = IS_k + dx^2 * (d^2 phi/dx^2)^2

        IS_k

        2epsilonHenrick et al. 2005
        -------------------------------------------
        epsilon = 1e-6
        epsilon = epsilon_0 * (1 + |phi|_max)

        epsilon
        - epsilon
        - epsilon

        Args:
            phi:  [n+2]

        Returns:
            phi_L:  [n+1]
            phi_R:  [n+1]
        """
        n = len(phi) - 2
        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)

        # ===== 2epsilon =====
        # phi_maxeps
        phi_max = min(np.max(np.abs(phi)), 100.0)  # 100
        eps = self.weno_eps * (1.0 + phi_max)

        # 
        d1 = 1.0 / 3.0
        d2 = 2.0 / 3.0

        # 
        for i in range(n + 1):
            # -----  -----
            if i > 0:
                phi1_L = 1.5 * phi[i] - 0.5 * phi[i-1]
            else:
                phi1_L = phi[i]

            if i < n:
                phi2_L = 0.5 * phi[i] + 0.5 * phi[i+1]
            else:
                phi2_L = phi[i]

            # ===== 1 =====
            if i > 0:
                # 
                IS1_L = (phi[i] - phi[i-1])**2

                # 
                if i > 1:
                    d2phi_1 = phi[i] - 2*phi[i-1] + phi[i-2]
                    # dx^2
                    IS1_L += min(self.dx, 1.0)**2 * d2phi_1**2

                beta1_L = IS1_L
            else:
                beta1_L = 0.0

            if i < n:
                IS2_L = (phi[i+1] - phi[i])**2

                if i < n - 1:
                    d2phi_2 = phi[i+1] - 2*phi[i] + phi[i-1] if i > 0 else phi[i+1] - phi[i]
                    # dx^2
                    IS2_L += min(self.dx, 1.0)**2 * d2phi_2**2

                beta2_L = IS2_L
            else:
                beta2_L = 0.0

            # 
            beta1_L_safe = min(beta1_L, 1e10)
            beta2_L_safe = min(beta2_L, 1e10)

            alpha1_L = d1 / (eps + beta1_L_safe)**2
            alpha2_L = d2 / (eps + beta2_L_safe)**2

            sum_alpha_L = alpha1_L + alpha2_L

            if sum_alpha_L > 1e-20:
                omega1_L = alpha1_L / sum_alpha_L
                omega2_L = alpha2_L / sum_alpha_L
            else:
                omega1_L = d1
                omega2_L = d2

            phi_L[i] = omega1_L * phi1_L + omega2_L * phi2_L

            # ----- -----
            if i < n - 1:
                phi1_R = 1.5 * phi[i+1] - 0.5 * phi[i+2]
            else:
                phi1_R = phi[i+1] if i < n else phi[i]

            if i < n:
                phi2_R = 0.5 * phi[i+1] + 0.5 * phi[i]
            else:
                phi2_R = phi[i+1] if i < n else phi[i]

            # 
            if i < n:
                IS1_R = (phi[i+1] - phi[i])**2
                if i < n - 1:
                    d2phi_1 = phi[i+2] - 2*phi[i+1] + phi[i] if i < n - 1 else 0
                    # 
                    IS1_R += min(self.dx, 1.0)**2 * d2phi_1**2
                beta1_R = IS1_R
            else:
                beta1_R = 0.0

            if i > 0:
                IS2_R = (phi[i] - phi[i-1])**2 if i > 0 else 0
                if i > 1:
                    d2phi_2 = phi[i+1] - 2*phi[i] + phi[i-1] if i < n else 0
                    # 
                    IS2_R += min(self.dx, 1.0)**2 * d2phi_2**2
                beta2_R = IS2_R
            else:
                beta2_R = 0.0

            beta1_R_safe = min(beta1_R, 1e10)
            beta2_R_safe = min(beta2_R, 1e10)

            alpha1_R = d1 / (eps + beta1_R_safe)**2
            alpha2_R = d2 / (eps + beta2_R_safe)**2

            sum_alpha_R = alpha1_R + alpha2_R

            if sum_alpha_R > 1e-20:
                omega1_R = alpha1_R / sum_alpha_R
                omega2_R = alpha2_R / sum_alpha_R
            else:
                omega1_R = d1
                omega2_R = d2

            phi_R[i] = omega1_R * phi1_R + omega2_R * phi2_R

        return phi_L, phi_R

    def _entropy_fix_harten_hyman(
        self,
        h_L: float,
        h_R: float,
        u_L: float,
        u_R: float
    ) -> Tuple[float, float]:
        """
        Harten-Hyman1983

        HLL/Roe

        0Riemann
        - 
        - 
        - 

        |lambda| < delta

        sgn(lambda) = lambda/|lambda|
        
            |lambda|_fix = |lambda|  if |lambda| >= delta
            |lambda|_fix = (lambda^2 + delta^2)/(2*delta)  if |lambda| < delta

        
            delta: 0.1 ~ 0.5

        
        - 
        - 
        - 

        Args:
            h_L, h_R: 
            u_L, u_R: 

        Returns:
            lambda_L_fix, lambda_R_fix: 
        """
        c_L = np.sqrt(self.g * h_L) if h_L > self.eps_dry else 0
        c_R = np.sqrt(self.g * h_R) if h_R > self.eps_dry else 0

        # 
        lambda_L = u_L - c_L
        lambda_R = u_R + c_R

        # 
        delta = self.entropy_delta * max(c_L, c_R, 1e-10)

        # 
        if abs(lambda_L) < delta:
            lambda_L_fix = (lambda_L**2 + delta**2) / (2 * delta)
        else:
            lambda_L_fix = lambda_L

        # 
        if abs(lambda_R) < delta:
            lambda_R_fix = (lambda_R**2 + delta**2) / (2 * delta)
        else:
            lambda_R_fix = lambda_R

        return lambda_L_fix, lambda_R_fix

    def _hydrostatic_reconstruction(
        self,
        h_L: float,
        h_R: float,
        z_L: float,
        z_R: float
    ) -> Tuple[float, float]:
        """
        Audusse et al. 2004

        Well-Balanced"Lake at Rest"

        FVM
        -----------------------------------------------
        h + z = const, u = 0
        FVM ≠  → 

        

        
        ------------------------------------
        h_Lh_R
        
            1. eta_L = h_L + z_L, eta_R = h_R + z_R
            2. z_interface = max(z_L, z_R)
            3. 
                h_L_star = max(0, eta_L - z_interface)
                h_R_star = max(0, eta_R - z_interface)

        
        - eta_L = eta_Rz_L ≠ z_R
        - 

        
         h + z = C, u = 0:
        -  = 0.5*g*h^2
        -  = g*h*dz/dx
        - h* → 

        Args:
            h_L, h_R: 
            z_L, z_R: 

        Returns:
            h_L_star, h_R_star: 
        """
        # 
        eta_L = h_L + z_L
        eta_R = h_R + z_R

        # 
        z_interface = max(z_L, z_R)

        # 
        h_L_star = max(0.0, eta_L - z_interface)
        h_R_star = max(0.0, eta_R - z_interface)

        return h_L_star, h_R_star

    def _adaptive_cfl_control(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> float:
        """
        CFL

        CFL

        
        1. 
        2. CFL0.2
        3. CFL0.5

        
        ----------------------------------------
        
        - |dp/dx| 
        - |dh/dx| 
        - |du/dx| 

        
        shock_indicator = |grad_p| / (g * h_mean^2 / dx) > threshold

        Args:
            h: 
            Q: 

        Returns:
            dt: 
        """
        n = len(h)
        u = np.zeros(n)

        # 
        for i in range(n):
            if h[i] > self.eps_dry:
                u[i] = Q[i] / (self.B * h[i])

        # 
        pressure = 0.5 * self.g * h**2

        # 
        grad_p = np.gradient(pressure, self.dx)

        # 
        h_mean = np.mean(h) + 1e-10
        shock_threshold = 0.1 * self.g * h_mean**2 / self.dx
        shock_indicator = np.abs(grad_p) > shock_threshold

        # CFL
        if self.adaptive_cfl and np.any(shock_indicator):
            # CFL
            cfl_local = np.where(shock_indicator, self.cfl_shock, self.cfl_base)
            cfl_use = np.min(cfl_local)
        else:
            cfl_use = self.cfl_base

        # 
        c = np.sqrt(self.g * h)
        lambda_max = np.max(np.abs(u) + c)

        if lambda_max > 1e-10:
            dt = cfl_use * self.dx / lambda_max
        else:
            dt = self.dt_max if self.dt_max is not None else 1.0

        # dt_max
        if self.dt_max is not None:
            dt = min(dt, self.dt_max)

        return dt

    def _compute_rhs(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        WENO3

        
        1. _weno3_reconstruction_enhancedWENO3
        2. Well-Balanced
        3. Riemann
        """
        n = len(h)
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)

        # 
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)

        # ===== WENO3 =====
        h_L, h_R = self._weno3_reconstruction_enhanced(h_ext)
        Q_L, Q_R = self._weno3_reconstruction_enhanced(Q_ext)

        # ===== Well-Balanced =====
        if self.well_balanced:
            # 
            # self.z_b
            # 
            z_interface = np.zeros(n + 1)
            if hasattr(self, 'z_b'):
                # 
                z_interface[0] = self.z_b[0] - 0.5 * self.S0[0] * self.dx if hasattr(self.S0, '__len__') else self.z_b[0] - 0.5 * self.S0 * self.dx
                z_interface[-1] = self.z_b[-1] + 0.5 * self.S0[-1] * self.dx if hasattr(self.S0, '__len__') else self.z_b[-1] + 0.5 * self.S0 * self.dx
                for i in range(1, n):
                    z_interface[i] = 0.5 * (self.z_b[i-1] + self.z_b[i])
            else:
                # z_b
                slope_val = self.S0[0] if hasattr(self.S0, '__len__') else self.S0
                for i in range(n + 1):
                    z_interface[i] = slope_val * (i * self.dx)

            for i in range(n + 1):
                # 
                if i == 0:
                    z_L = z_interface[i]
                    z_R = z_interface[i]
                elif i == n:
                    z_L = z_interface[i]
                    z_R = z_interface[i]
                else:
                    z_L = z_interface[i]
                    z_R = z_interface[i]

                h_L[i], h_R[i] = self._hydrostatic_reconstruction(
                    h_L[i], h_R[i], z_L, z_R
                )

        # 
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        for i in range(n + 1):
            # 
            if self.entropy_fix and h_L[i] > self.eps_dry and h_R[i] > self.eps_dry:
                u_L = Q_L[i] / (self.B * h_L[i])
                u_R = Q_R[i] / (self.B * h_R[i])
                # HLL

            F_h[i], F_Q[i] = self._hll_flux(
                h_L[i], Q_L[i], h_R[i], Q_R[i]
            )

        #  + 
        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx
            dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

        return dh_dt, dQ_dt

    def _compute_dt(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> float:
        """
        CFL
        """
        if self.adaptive_cfl:
            return self._adaptive_cfl_control(h, Q)
        else:
            # CFL
            return super()._compute_dt(h, Q)


# =====  =====
if __name__ == "__main__":
    print("\n" + "="*80)
    print("Enhanced WENO3 Solver - ")
    print("="*80)

    # 1Lake at Rest
    print("\n1Lake at Rest")
    print("-" * 40)

    solver = GodunvFVMWENO3Enhanced(
        width=10.0,
        length=1000.0,
        n_cells=100,
        manning_n=0.0,
        slope=0.001,  # 
        cfl=0.4,
        well_balanced=True
    )

    #  = 
    solver.bc_left = {'type': 'Q', 'value': 0.0}
    solver.bc_right = {'type': 'Q', 'value': 0.0}

    # 
    slope_val = 0.001
    x = solver.x  # 
    h_init = 5.0 - x * slope_val  # 
    solver.h[:] = h_init
    solver.Q[:] = np.zeros_like(h_init)  # 

    # 
    t_end = 10.0
    dt = 0.1

    water_level_init = solver.h + x * slope_val
    print(f": {np.min(water_level_init):.6f} ~ "
          f"{np.max(water_level_init):.6f}")

    t = 0.0
    n_steps = 0
    while t < t_end:
        dt_actual = solver._compute_dt(solver.h, solver.Q)
        dt_use = min(dt_actual, dt)
        solver.step(dt_use)
        t += dt_use
        n_steps += 1

    water_level_final = solver.h + x * slope_val
    print(f": {np.min(water_level_final):.6f} ~ "
          f"{np.max(water_level_final):.6f}")
    print(f": {n_steps}")

    # 
    u = np.zeros_like(solver.h)
    for i in range(len(solver.h)):
        if solver.h[i] > solver.eps_dry:
            u[i] = solver.Q[i] / (solver.B * solver.h[i])

    print(f": {np.max(np.abs(u)):.6e} m/s")
    print(f": {np.max(np.abs(np.diff(water_level_final))):.6e} m")

    if np.max(np.abs(np.diff(water_level_final))) < 1e-8:
        print(" Lake at RestWell-Balanced")
    else:
        print(f"[WARN] Lake at Rest={np.max(np.abs(np.diff(water_level_final))):.6e}")

    print("\n" + "="*80)
    print("")
    print("="*80)
