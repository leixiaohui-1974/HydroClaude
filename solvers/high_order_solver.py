#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""



1. MUSCL
2. Runge-Kutta



: Claude
: 2025-10-23
"""

import numpy as np
from typing import Tuple, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


class HighOrderCanalSolver(HydrostaticCanalSolver):
    """
    

    
    - MUSCL → 
    - RK2 → 
    """

    def __init__(self, *args, muscl_limiter: str = 'minmod', **kwargs):
        """
        Args:
            muscl_limiter: MUSCL ('minmod', 'superbee', 'vanleer')
        """
        super().__init__(*args, **kwargs)
        self.muscl_limiter = muscl_limiter
        self.use_muscl = True  # MUSCL

    def minmod(self, a: float, b: float) -> float:
        """
        Minmod

        minmod(a,b) = sgn(a) * max(0, min(|a|, sgn(a)*b))
        """
        if a * b <= 0:
            return 0.0
        return np.sign(a) * min(abs(a), abs(b))

    def superbee(self, a: float, b: float) -> float:
        """
        Superbee
        """
        if a * b <= 0:
            return 0.0
        return np.sign(a) * max(min(2*abs(a), abs(b)), min(abs(a), 2*abs(b)))

    def vanleer(self, a: float, b: float) -> float:
        """
        Van Leer
        """
        if a * b <= 0:
            return 0.0
        return 2 * a * b / (a + b)

    def apply_limiter(self, a: float, b: float) -> float:
        """"""
        if self.muscl_limiter == 'minmod':
            return self.minmod(a, b)
        elif self.muscl_limiter == 'superbee':
            return self.superbee(a, b)
        elif self.muscl_limiter == 'vanleer':
            return self.vanleer(a, b)
        else:
            return self.minmod(a, b)  # minmod

    def muscl_reconstruct(self, U: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        MUSCL

        TVD

        Args:
            U:  [nx]

        Returns:
            U_L:  [nx+1]
            U_R:  [nx+1]
        """
        nx = len(U)

        # 
        U_ext = np.zeros(nx + 2)
        U_ext[1:-1] = U
        U_ext[0] = U[0]  # 
        U_ext[-1] = U[-1]  # 

        # 
        U_L = np.zeros(nx + 1)  # ii-1
        U_R = np.zeros(nx + 1)  # ii

        for i in range(nx + 1):
            # ii-1i
            # ii+1

            # i-1
            if i > 0:
                # i-1
                dU_backward = U_ext[i] - U_ext[i-1]  # 
                dU_forward = U_ext[i+1] - U_ext[i]  # 
                slope_L = self.apply_limiter(dU_backward, dU_forward)
                U_L[i] = U_ext[i] + 0.5 * slope_L
            else:
                U_L[i] = U_ext[1]

            # i
            if i < nx:
                # i
                dU_backward = U_ext[i+1] - U_ext[i]
                dU_forward = U_ext[i+2] - U_ext[i+1]
                slope_R = self.apply_limiter(dU_backward, dU_forward)
                U_R[i] = U_ext[i+1] - 0.5 * slope_R
            else:
                U_R[i] = U_ext[nx]

        return U_L, U_R

    def compute_fluxes_muscl(self, h: np.ndarray, hu: np.ndarray,
                            z: np.ndarray, dx: float) -> Tuple[np.ndarray, np.ndarray,
                                                               np.ndarray, np.ndarray]:
        """
        MUSCL

        
        1. MUSCL
        2. 
        3. HLL Riemann
        4. Audusse

        Args:
            h, hu, z: 
            dx: 

        Returns:
            (F_mass, F_momentum, S_mass, S_momentum)
        """
        if not self.use_muscl:
            # 
            return self.compute_fluxes_and_sources(h, hu, z, dx)

        nx = len(h)

        # MUSCL
        h_L, h_R = self.muscl_reconstruct(h)
        hu_L, hu_R = self.muscl_reconstruct(hu)

        # 
        z_ext = np.zeros(nx + 2)
        z_ext[1:-1] = z
        z_ext[0] = z[0]
        z_ext[-1] = z[-1]

        # 
        F_mass = np.zeros(nx + 1)
        F_momentum = np.zeros(nx + 1)
        h_star_interfaces = np.zeros((nx + 1, 2))

        # 
        for i in range(nx + 1):
            # i
            h_left = h_L[i]
            hu_left = hu_L[i]
            z_left = z_ext[i]

            h_right = h_R[i]
            hu_right = hu_R[i]
            z_right = z_ext[i+1]

            # 
            z_max = max(z_left, z_right)
            h_star_L = max(0.0, h_left + z_left - z_max)
            h_star_R = max(0.0, h_right + z_right - z_max)

            h_star_interfaces[i, 0] = h_star_L
            h_star_interfaces[i, 1] = h_star_R

            # HLL
            F_mass_i, F_mom_i = self.hll_flux(h_star_L, hu_left,
                                              h_star_R, hu_right)
            F_mass[i] = F_mass_i
            F_momentum[i] = F_mom_i

        # Audusse
        S_mass = np.zeros(nx)
        S_momentum = np.zeros(nx)

        for i in range(nx):
            # 0
            S_mass[i] = 0.0

            # Audusse
            h_star_L = h_star_interfaces[i, 1]  # 
            h_star_R = h_star_interfaces[i+1, 0]  # 

            S_hydrostatic = 0.5 * self.g * (h_star_R**2 - h_star_L**2) / dx

            # 
            if h[i] > self.eps_dry:
                u = hu[i] / h[i]
                R = (self.B * h[i]) / (self.B + 2 * h[i])
                S_friction = -self.g * self.n**2 * abs(u) * u / (R**(4/3))
            else:
                S_friction = 0.0

            S_momentum[i] = S_hydrostatic + S_friction

        return F_mass, F_momentum, S_mass, S_momentum

    def step_rk2(self, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Runge-KuttaHeun

        RK2
        U^(1) = U^n + dt * F(U^n)
        U^(n+1) = U^n + dt/2 * (F(U^n) + F(U^(1)))

        Args:
            dt: 

        Returns:
            (h_new, hu_new): 
        """
        # 
        F_mass_1, F_mom_1, S_mass_1, S_mom_1 = self.compute_fluxes_muscl(
            self.h, self.hu, self.z, self.dx
        )

        h_star = self.h.copy()
        hu_star = self.hu.copy()

        for i in range(self.nx):
            dh = dt * (-(F_mass_1[i+1] - F_mass_1[i])/self.dx + S_mass_1[i])
            dhu = dt * (-(F_mom_1[i+1] - F_mom_1[i])/self.dx + S_mom_1[i])

            h_star[i] = self.h[i] + dh
            hu_star[i] = self.hu[i] + dhu

            # 
            h_star[i] = max(0.0, h_star[i])

        # 
        F_mass_2, F_mom_2, S_mass_2, S_mom_2 = self.compute_fluxes_muscl(
            h_star, hu_star, self.z, self.dx
        )

        # 
        h_new = self.h.copy()
        hu_new = self.hu.copy()

        for i in range(self.nx):
            # 
            dh_1 = -(F_mass_1[i+1] - F_mass_1[i])/self.dx + S_mass_1[i]
            dhu_1 = -(F_mom_1[i+1] - F_mom_1[i])/self.dx + S_mom_1[i]

            # 
            dh_2 = -(F_mass_2[i+1] - F_mass_2[i])/self.dx + S_mass_2[i]
            dhu_2 = -(F_mom_2[i+1] - F_mom_2[i])/self.dx + S_mom_2[i]

            # RK2
            h_new[i] = self.h[i] + dt * 0.5 * (dh_1 + dh_2)
            hu_new[i] = self.hu[i] + dt * 0.5 * (dhu_1 + dhu_2)

            # 
            h_new[i] = max(0.0, h_new[i])

        return h_new, hu_new

    def solve_transient_high_order(
        self,
        t_end: float,
        dt: float = 0.1,
        Q_upstream: float = None,
        h_downstream: float = None,
        Q_upstream_func: callable = None,
        h_downstream_func: callable = None,
        save_interval: int = 10,
        verbose: bool = True,
        use_muscl: bool = True,
        use_rk2: bool = True
    ) -> dict:
        """
        

        Args:
            t_end: 
            dt: 
            Q_upstream: 
            h_downstream: 
            Q_upstream_func: 
            h_downstream_func: 
            save_interval: 
            verbose: 
            use_muscl: MUSCL
            use_rk2: RK2

        Returns:
            result: 
        """
        self.use_muscl = use_muscl

        # 
        self.h_history = []
        self.Q_history = []
        self.t_history = []

        # 
        if Q_upstream_func is None:
            Q_upstream_func = lambda t: Q_upstream
        if h_downstream_func is None:
            h_downstream_func = lambda t: h_downstream

        t = 0.0
        n_steps = int(t_end / dt)

        method_str = f"{'MUSCL' if use_muscl else '1st-order'} + {'RK2' if use_rk2 else 'Euler'}"

        if verbose:
            print(f"{method_str}")
            print(f"  : 0 → {t_end} s")
            print(f"  : {dt} s")
            print(f"  : {n_steps}")
            print(f"  MUSCL: {self.muscl_limiter}")

        # 
        self.h_history.append(self.h.copy())
        self.Q_history.append(self.get_Q().copy())
        self.t_history.append(t)

        # 
        for step in range(n_steps):
            t = (step + 1) * dt
            self.current_time = t

            # 
            Q_in = Q_upstream_func(t)
            h_out = h_downstream_func(t)

            # 
            if use_rk2:
                h_new, hu_new = self.step_rk2(dt)
            else:
                # 
                F_mass, F_mom, S_mass, S_mom = self.compute_fluxes_muscl(
                    self.h, self.hu, self.z, self.dx
                )
                h_new = self.h.copy()
                hu_new = self.hu.copy()
                for i in range(self.nx):
                    dh = dt * (-(F_mass[i+1] - F_mass[i])/self.dx + S_mass[i])
                    dhu = dt * (-(F_mom[i+1] - F_mom[i])/self.dx + S_mom[i])
                    h_new[i] = self.h[i] + dh
                    hu_new[i] = self.hu[i] + dhu
                    h_new[i] = max(0.0, h_new[i])

            # 
            hu_new[0] = Q_in / self.B
            h_new[-1] = h_out

            # 
            self.h = h_new
            self.hu = hu_new

            # 
            if self.structure_indices:
                self._apply_internal_bc(t=t, Q_target=Q_in,
                                      max_iter=20, tol=0.05, relax=0.6)

            # 
            if (step + 1) % save_interval == 0:
                self.h_history.append(self.h.copy())
                self.Q_history.append(self.get_Q().copy())
                self.t_history.append(t)

            # 
            if verbose and (step + 1) % max(n_steps // 10, 1) == 0:
                Q_mean = np.mean(self.get_Q())
                h_mean = np.mean(self.h)
                print(f"  t={t:.2f}s ({(step+1)/n_steps*100:.1f}%): " +
                      f"Q={Q_mean:.3f} m³/s, h_avg={h_mean:.3f} m")

        # 
        if verbose:
            print(f"\n")
            print(f"  : {len(self.t_history)}")
            print(f"  : {np.mean(self.get_Q()):.3f} m³/s")
            print(f"  : [{self.h.min():.3f}, {self.h.max():.3f}] m")

        result = {
            't_history': np.array(self.t_history),
            'h_history': np.array(self.h_history),
            'Q_history': np.array(self.Q_history),
            'h_final': self.h.copy(),
            'Q_final': self.get_Q().copy(),
            'x': self.x.copy(),
            'method': method_str
        }

        return result


# 
if __name__ == "__main__":
    print("=" * 70)
    print("")
    print("=" * 70)

    # 
    solver = HighOrderCanalSolver(
        length=1000.0, nx=101, B=10.0, S0=0.001, n=0.025,
        muscl_limiter='minmod'
    )

    # 
    solver.h = np.ones(101) * 0.6
    solver.hu = np.ones(101) * 5.0 / 10.0

    # 
    def Q_func(t):
        return 5.0 if t < 50.0 else 10.0

    # 
    result = solver.solve_transient_high_order(
        t_end=100.0,
        dt=0.5,
        Q_upstream_func=Q_func,
        h_downstream=0.6,
        save_interval=5,
        use_muscl=True,
        use_rk2=True
    )

    print(f"\n")
    print(f": {result['method']}")
