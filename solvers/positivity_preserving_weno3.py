#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WENO3 (Positivity-Preserving WENO3)

Zhang-Shu (2010)
1. RP290% → <30%
2. 
3. h≥0


- WENO3
- θ
- 


- Zhang, X., & Shu, C. W. (2010). "Positivity-preserving high order finite
  difference WENO schemes for compressible Euler equations."
  Journal of Computational Physics, 229(23), 8918-8934.
- Zhang, X., Shu, C. W., & Zhang, Q. (2012). "Maximum-principle-satisfying
  and positivity-preserving high order schemes for conservation laws."
  SIAM Journal on Scientific Computing, 34(2), A627-A658.

: HydroClaude Team
: 2025-10-31
: Stage 8 - Phase 8.1
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3


class PositivityPreservingWENO3(GodunvFVMWENO3):
    """
    WENO3

    GodunvFVMWENO3
    1. WENO3
    2. 
    3. h≥0

    
    - 3
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
        eps_pp: float = 1e-10,
        theta_min: float = 0.0,
        use_pp: bool = True,
        **kwargs
    ):
        """
        WENO3

        Args:
            (GodunvFVMWENO3)
            eps_pp: h≥eps_pp
            theta_min: 0-10=1=
            use_pp: 
        """
        # 
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            **kwargs
        )

        self.eps_pp = eps_pp
        self.theta_min = theta_min
        self.use_pp = use_pp

        # 
        self.pp_activations = 0  # 
        self.theta_values = []    # 

        print(f" WENO3")
        print(f"  : eps_pp = {self.eps_pp}")
        print(f"  : theta_min = {self.theta_min}")
        print(f"  : {'' if use_pp else ''}")

    def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        WENO3
        1. WENO3
        2. HLL
        3. h≥eps_pp

        Returns:
            dh_dt, dQ_dt: 
        """
        n = len(h)

        # 
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)

        if not self.use_pp:
            # WENO3
            return super()._compute_rhs(h, Q)

        # ===== Step 1: WENO3 =====
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)
        h_L_weno, h_R_weno = self._weno3_reconstruction(h_ext)
        Q_L_weno, Q_R_weno = self._weno3_reconstruction(Q_ext)

        F_h_weno = np.zeros(n + 1)
        F_Q_weno = np.zeros(n + 1)

        for i in range(n + 1):
            F_h_weno[i], F_Q_weno[i] = self._hll_flux(
                h_L_weno[i], Q_L_weno[i], h_R_weno[i], Q_R_weno[i]
            )

        # ===== Step 2: HLL=====
        F_h_first = np.zeros(n + 1)
        F_Q_first = np.zeros(n + 1)

        for i in range(n + 1):
            # cell
            if i == 0:
                h_L_first = h[0]
                Q_L_first = Q[0]
            else:
                h_L_first = h[i-1]
                Q_L_first = Q[i-1]

            if i == n:
                h_R_first = h[-1]
                Q_R_first = Q[-1]
            else:
                h_R_first = h[i]
                Q_R_first = Q[i]

            F_h_first[i], F_Q_first[i] = self._hll_flux(
                h_L_first, Q_L_first, h_R_first, Q_R_first
            )

        # ===== Step 3: θ =====
        theta = self._compute_positivity_limiter(
            h, Q, F_h_weno, F_Q_weno, F_h_first, F_Q_first
        )

        # ===== Step 4:  =====
        F_h = theta * F_h_weno + (1 - theta) * F_h_first
        F_Q = theta * F_Q_weno + (1 - theta) * F_Q_first

        # ===== Step 5:  =====
        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx

            # 
            dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

        # 
        if np.any(theta < 0.99):
            self.pp_activations += 1
            self.theta_values.append(np.min(theta))

        return dh_dt, dQ_dt

    def _compute_positivity_limiter(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        F_h_weno: np.ndarray,
        F_Q_weno: np.ndarray,
        F_h_first: np.ndarray,
        F_Q_first: np.ndarray
    ) -> np.ndarray:
        """
        θ

        Zhang-Shu (2010)
        θ = min(1, (h_i - eps_pp) / (h_i - h_new_weno))

        Args:
            h, Q: 
            F_h_weno, F_Q_weno: WENO3
            F_h_first, F_Q_first: 

        Returns:
            theta:  [n+1]
        """
        n = len(h)
        theta = np.ones(n + 1)  # 

        # WENO3
        h_new_weno = h.copy()
        for i in range(n):
            h_new_weno[i] = h[i] - self.dt / self.dx * (F_h_weno[i+1] - F_h_weno[i])

        # 
        h_new_first = h.copy()
        for i in range(n):
            h_new_first[i] = h[i] - self.dt / self.dx * (F_h_first[i+1] - F_h_first[i])

        # cell
        for i in range(n):
            if h_new_weno[i] < self.eps_pp:
                # WENO3h < eps_pp

                # 
                # h_new = h - dt/dx * (F_mixed[i+1] - F_mixed[i]) >= eps_pp
                # F_mixed = theta * F_weno + (1-theta) * F_first

                if h_new_first[i] >= self.eps_pp:
                    # 
                    numerator = h[i] - self.eps_pp
                    denominator = h[i] - h_new_weno[i]

                    if abs(denominator) > 1e-14:
                        theta_i = numerator / denominator
                        theta_i = np.clip(theta_i, self.theta_min, 1.0)
                    else:
                        theta_i = 1.0
                else:
                    # theta
                    theta_i = self.theta_min

                # 
                if i > 0:
                    theta[i] = min(theta[i], theta_i)
                if i < n - 1:
                    theta[i+1] = min(theta[i+1], theta_i)

        return theta

    def get_statistics(self) -> Dict[str, any]:
        """
        

        Returns:
            dict: theta
        """
        stats = {
            'pp_activations': self.pp_activations,
            'total_steps': self.step_count if hasattr(self, 'step_count') else 0,
            'activation_rate': 0.0,
            'min_theta': 1.0,
            'avg_theta': 1.0,
            'theta_history': self.theta_values
        }

        if hasattr(self, 'step_count') and self.step_count > 0:
            stats['activation_rate'] = self.pp_activations / self.step_count

        if len(self.theta_values) > 0:
            stats['min_theta'] = np.min(self.theta_values)
            stats['avg_theta'] = np.mean(self.theta_values)

        return stats

    def print_statistics(self):
        """"""
        stats = self.get_statistics()

        print("\n" + "="*60)
        print("")
        print("="*60)
        print(f": {stats['total_steps']}")
        print(f": {stats['pp_activations']}")
        print(f": {stats['activation_rate']*100:.2f}%")

        if len(self.theta_values) > 0:
            print(f"θ: {stats['min_theta']:.6f}")
            print(f"θ: {stats['avg_theta']:.6f}")
            print(f": θ=1.0θ<1.0θ=0.0")
        else:
            print("")

        print("="*60)


class PositivityPreservingWENO3Enhanced(PositivityPreservingWENO3):
    """
    WENO3

    
    1. eps_pp
    2. 
    3. 
    """

    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        adaptive_eps: bool = True,
        wet_dry_threshold: float = 1e-4,
        **kwargs
    ):
        """
        

        Args:
            adaptive_eps: eps_pp
            wet_dry_threshold: 
        """
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            **kwargs
        )

        self.adaptive_eps = adaptive_eps
        self.wet_dry_threshold = wet_dry_threshold

        print(f" eps_pp + ")

    def _detect_wet_dry_interface(self, h: np.ndarray) -> np.ndarray:
        """
        

        Args:
            h: 

        Returns:
            mask: True
        """
        n = len(h)
        mask = np.zeros(n, dtype=bool)

        for i in range(n):
            # cellcells
            cells_to_check = []
            if i > 0:
                cells_to_check.append(h[i-1])
            cells_to_check.append(h[i])
            if i < n - 1:
                cells_to_check.append(h[i+1])

            # 
            has_wet = any(h_val > self.wet_dry_threshold for h_val in cells_to_check)
            has_dry = any(h_val <= self.wet_dry_threshold for h_val in cells_to_check)

            mask[i] = has_wet and has_dry

        return mask

    def _compute_positivity_limiter(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        F_h_weno: np.ndarray,
        F_Q_weno: np.ndarray,
        F_h_first: np.ndarray,
        F_Q_first: np.ndarray
    ) -> np.ndarray:
        """
        
        """
        # 
        theta = super()._compute_positivity_limiter(
            h, Q, F_h_weno, F_Q_weno, F_h_first, F_Q_first
        )

        # 
        wd_mask = self._detect_wet_dry_interface(h)

        # 
        for i in range(len(h)):
            if wd_mask[i]:
                # theta
                if i > 0:
                    theta[i] = min(theta[i], 0.5)  # 50%
                if i < len(h) - 1:
                    theta[i+1] = min(theta[i+1], 0.5)

        return theta


# =====  =====

def create_pp_weno3_solver(config: Dict) -> PositivityPreservingWENO3:
    """
    WENO3

    Args:
        config: 

    Returns:
        solver: PositivityPreservingWENO3
    """
    return PositivityPreservingWENO3(**config)


def test_positivity_preservation():
    """
    
    """
    print("\n" + "="*70)
    print("WENO3 - ")
    print("="*70)

    # 
    solver = PositivityPreservingWENO3(
        width=10.0,
        length=100.0,
        n_cells=500,
        manning_n=0.0,
        slope=0.0,
        cfl=0.2,
        eps_pp=1e-10,
        use_numba=False  # Numba
    )

    # RP2
    x_dam = 50.0
    h_L, u_L = 5.0, 5.0
    h_R, u_R = 5.0, -5.0

    x = solver.x
    h_init = np.where(x <= x_dam, h_L, h_R)
    Q_init = solver.B * np.where(x <= x_dam, h_L * u_L, h_R * u_R)

    bc_left = {'type': 'transmissive'}
    bc_right = {'type': 'transmissive'}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 
    print(f"\n: [{np.min(h_init):.6f}, {np.max(h_init):.6f}]")

    for step in range(10):
        solver.step()
        h_min = np.min(solver.h)
        h_max = np.max(solver.h)

        print(f"Step {step+1}: h ∈ [{h_min:.6f}, {h_max:.6f}], t={solver.t:.4f}s")

        # 
        if h_min < 0:
            print(f"   h_min = {h_min}")
            break
        else:
            print(f"   ")

    # 
    solver.print_statistics()

    print("\n")
    print("="*70)


if __name__ == '__main__':
    # 
    test_positivity_preservation()
