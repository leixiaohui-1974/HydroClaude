#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WENO3Phase 8.2


1. Phase 8.1
2. 
3. 
4. 


- RP5-RP7>400% → <50%
- <0.1%
- h≥0


- Toro, E.F. (2001). Shock-Capturing Methods for Free-Surface Shallow Flows.
- Zhang, X., & Shu, C.W. (2010). Positivity-preserving high order finite difference WENO schemes.
- Audusse, E., et al. (2004). A fast and stable well-balanced scheme with hydrostatic reconstruction.

: HydroClaude Team
: 2025-10-31
: Stage 8 - Phase 8.2
"""

import numpy as np
from typing import Tuple, Dict, Optional
from solvers.positivity_preserving_weno3 import PositivityPreservingWENO3


class WetDryEnhancedWENO3(PositivityPreservingWENO3):
    """
    WENO3Phase 8.2

    
    GodunvFVMSolver → GodunvFVMWENO3 → PositivityPreservingWENO3 → WetDryEnhancedWENO3

    
    1. _detect_wet_dry_interface
    2. _hll_flux_wet_dry
    3. 
    4. 
    """

    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float,
        g: float = 9.81,
        cfl: float = 0.2,
        eps_dry: float = 1e-6,
        eps_pp: float = 1e-10,
        theta_min: float = 0.0,
        wet_dry_threshold: float = 1e-4,
        interface_theta_max: float = 0.3,
        use_pp: bool = True,
        use_wd_flux: bool = True,
        use_enhanced_bc: bool = True,
        well_balanced: bool = False,
        use_numba: bool = False,
        **kwargs
    ):
        """
        WENO3

        Args:
            ... ()
            wet_dry_threshold: 1e-4
            interface_theta_max: θ0.3
            use_wd_flux: True
        """
        # Phase 8.1
        super().__init__(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=slope,
            g=g,
            cfl=cfl,
            eps_dry=eps_dry,
            eps_pp=eps_pp,
            theta_min=theta_min,
            use_pp=use_pp,
            use_enhanced_bc=use_enhanced_bc,
            well_balanced=well_balanced,
            use_numba=use_numba,
            **kwargs
        )

        # Phase 8.2
        self.wet_dry_threshold = wet_dry_threshold
        self.interface_theta_max = interface_theta_max
        self.use_wd_flux = use_wd_flux

        # 
        self.wd_activations = 0  # 
        self.interface_type_counts = {
            'wet_to_dry': 0,
            'dry_to_wet': 0,
            'vacuum_forming': 0
        }

        # 
        self.initial_mass = None
        self.mass_history = []

        print(f"\n{'='*70}")
        print("WENO3Phase 8.2")
        print(f"{'='*70}")
        print(f": WENO3Phase 8.1")
        print(f": {self.wet_dry_threshold}")
        print(f"θ: {self.interface_theta_max}")
        print(f": {'' if self.use_wd_flux else ''}")
        print(f"{'='*70}\n")

    def _detect_wet_dry_interface(self, h: np.ndarray) -> Dict:
        """
        

        Args:
            h: 

        Returns:
            dict: 
                - is_interface[i]: cell i
                - interface_type[i]: 
                - n_interfaces: 
        """
        n = len(h)
        is_interface = np.zeros(n, dtype=bool)
        interface_type = ['none'] * n

        for i in range(n):
            # 
            h_left = h[i-1] if i > 0 else h[i]
            h_center = h[i]
            h_right = h[i+1] if i < n-1 else h[i]

            # 
            neighbors = [h_left, h_center, h_right]
            has_wet = any(h_val > self.wet_dry_threshold for h_val in neighbors)
            has_dry = any(h_val <= self.wet_dry_threshold for h_val in neighbors)

            if has_wet and has_dry:
                is_interface[i] = True

                # 
                if h_center > self.wet_dry_threshold:
                    #  → wet_to_dry
                    if h_left <= self.wet_dry_threshold or h_right <= self.wet_dry_threshold:
                        interface_type[i] = 'wet_to_dry'
                else:
                    #  → dry_to_wet
                    if h_left > self.wet_dry_threshold or h_right > self.wet_dry_threshold:
                        interface_type[i] = 'dry_to_wet'

                # RP7
                if (h_center <= self.wet_dry_threshold and
                    h_left > self.wet_dry_threshold and
                    h_right > self.wet_dry_threshold):
                    interface_type[i] = 'vacuum_forming'

        n_interfaces = np.sum(is_interface)

        return {
            'is_interface': is_interface,
            'interface_type': interface_type,
            'n_interfaces': n_interfaces
        }

    def _is_interface_face(self, face_idx: int, interface_info: Dict) -> bool:
        """
        face

        Args:
            face_idx: 0n
            interface_info: 

        Returns:
            bool: 
        """
        is_interface = interface_info['is_interface']
        n = len(is_interface)

        # face i+1/2 cell icell i+1
        # face
        is_wd_face = False

        if face_idx > 0 and face_idx <= n:
            # cell (i-1)
            if is_interface[face_idx - 1]:
                is_wd_face = True

        if face_idx >= 0 and face_idx < n:
            # cell (i)
            if is_interface[face_idx]:
                is_wd_face = True

        return is_wd_face

    def _hll_flux_wet_dry(
        self,
        h_L: float,
        Q_L: float,
        h_R: float,
        Q_R: float
    ) -> Tuple[float, float]:
        """
        HLL

        : Toro (2001), Section 5.4

        
        1.  → 
        2.  → RP5
        3.  → RP6
        4.  → HLL

        Args:
            h_L, Q_L: 
            h_R, Q_R: 

        Returns:
            F_h, F_Q: 
        """
        # 
        dry_L = h_L < self.eps_dry
        dry_R = h_R < self.eps_dry

        # Case 1: 
        if dry_L and dry_R:
            return 0.0, 0.0

        # Case 2: RP5
        if dry_L and not dry_R:
            # 
            A_R = max(h_R * self.B, self.eps_dry * self.B)
            u_R = Q_R / A_R
            c_R = np.sqrt(self.g * h_R)

            # 
            S_R = u_R + 2.0 * c_R

            if S_R <= 0.0:
                # RP5
                F_h = Q_R
                F_Q = Q_R**2 / A_R + 0.5 * self.g * h_R**2 * self.B
            else:
                # 
                # 
                F_h = 0.0
                F_Q = 0.0

            return F_h, F_Q

        # Case 3: RP6
        if not dry_L and dry_R:
            # 
            A_L = max(h_L * self.B, self.eps_dry * self.B)
            u_L = Q_L / A_L
            c_L = np.sqrt(self.g * h_L)

            # 
            S_L = u_L - 2.0 * c_L

            if S_L >= 0.0:
                # RP6
                F_h = Q_L
                F_Q = Q_L**2 / A_L + 0.5 * self.g * h_L**2 * self.B
            else:
                # 
                # 
                F_h = 0.0
                F_Q = 0.0

            return F_h, F_Q

        # Case 4: HLL
        # HLL
        return self._hll_flux(h_L, Q_L, h_R, Q_R)

    def _compute_wet_dry_flux(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        interface_info: Dict
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        faces

        Args:
            h: 
            Q: 
            interface_info: 

        Returns:
            F_h, F_Q: n+1
        """
        n = len(h)
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        for i in range(n + 1):
            # 
            if i == 0:
                # ghost cell
                h_L = h[0]
                Q_L = Q[0]
            else:
                h_L = h[i-1]
                Q_L = Q[i-1]

            if i == n:
                # 
                h_R = h[-1]
                Q_R = Q[-1]
            else:
                h_R = h[i]
                Q_R = Q[i]

            # HLL
            F_h[i], F_Q[i] = self._hll_flux_wet_dry(h_L, Q_L, h_R, Q_R)

        return F_h, F_Q

    def _compute_positivity_limiter_enhanced(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        F_h_weno: np.ndarray,
        F_Q_weno: np.ndarray,
        F_h_first: np.ndarray,
        F_Q_first: np.ndarray,
        interface_info: Dict
    ) -> np.ndarray:
        """
        

        
        -  θ <= interface_theta_max0.3
        - θ=0

        Args:
            ... (Phase 8.1)
            interface_info: 

        Returns:
            theta: n+1
        """
        # Phase 8.1
        theta = self._compute_positivity_limiter(
            h, Q, F_h_weno, F_Q_weno, F_h_first, F_Q_first
        )

        # 
        is_interface = interface_info['is_interface']
        interface_type = interface_info['interface_type']
        n = len(h)

        for i in range(n + 1):
            # face i+1/2cell
            cells_to_check = []
            if i > 0:
                cells_to_check.append(i - 1)
            if i < n:
                cells_to_check.append(i)

            # cells
            for cell_idx in cells_to_check:
                if is_interface[cell_idx]:
                    # θ
                    theta[i] = min(theta[i], self.interface_theta_max)

                    # 
                    if interface_type[cell_idx] == 'vacuum_forming':
                        theta[i] = 0.0

        return theta

    def _compute_rhs(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        
        0. 
        1. WENO3
        2. 
        3. 
        4. 
        5. 
        6. 

        Args:
            h: 
            Q: 

        Returns:
            dh_dt, dQ_dt: 
        """
        n = len(h)

        # === Step 0:  ===
        interface_info = self._detect_wet_dry_interface(h)
        n_interfaces = interface_info['n_interfaces']

        # === Step 1: WENO3 ===
        # 
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)

        # WENO3
        h_L_weno, h_R_weno = self._weno3_reconstruction(h_ext)
        Q_L_weno, Q_R_weno = self._weno3_reconstruction(Q_ext)

        # WENO3
        F_h_weno = np.zeros(n + 1)
        F_Q_weno = np.zeros(n + 1)

        for i in range(n + 1):
            F_h_weno[i], F_Q_weno[i] = self._hll_flux(
                h_L_weno[i], Q_L_weno[i], h_R_weno[i], Q_R_weno[i]
            )

        # === Step 2: HLL ===
        F_h_first = np.zeros(n + 1)
        F_Q_first = np.zeros(n + 1)

        for i in range(n + 1):
            # 
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

        # === Step 3:  ===
        if self.use_wd_flux and n_interfaces > 0:
            F_h_wd, F_Q_wd = self._compute_wet_dry_flux(h, Q, interface_info)
        else:
            F_h_wd = None
            F_Q_wd = None

        # === Step 4: θ ===
        if self.use_pp:
            theta = self._compute_positivity_limiter_enhanced(
                h, Q, F_h_weno, F_Q_weno, F_h_first, F_Q_first, interface_info
            )
        else:
            theta = np.ones(n + 1)

        # === Step 5:  ===
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        wd_flux_used = 0

        for i in range(n + 1):
            # 
            is_wd_face = self._is_interface_face(i, interface_info)

            if self.use_wd_flux and is_wd_face and F_h_wd is not None:
                # 
                F_h[i] = F_h_wd[i]
                F_Q[i] = F_Q_wd[i]
                wd_flux_used += 1
            else:
                # Phase 8.1
                F_h[i] = theta[i] * F_h_weno[i] + (1.0 - theta[i]) * F_h_first[i]
                F_Q[i] = theta[i] * F_Q_weno[i] + (1.0 - theta[i]) * F_Q_first[i]

        # 
        if wd_flux_used > 0:
            self.wd_activations += 1
            for i in range(n):
                if interface_info['is_interface'][i]:
                    itype = interface_info['interface_type'][i]
                    self.interface_type_counts[itype] += 1

        # === Step 6:  ===
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)

        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx
            dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

        return dh_dt, dQ_dt

    def step(self, dt: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        Args:
            dt: 

        Returns:
            h, Q: 
        """
        # step
        h, Q = super().step(dt)

        # 
        self._check_mass_conservation()

        return h, Q

    def _check_mass_conservation(self):
        """
        

        
        """
        # 
        total_mass = np.sum(self.h * self.dx * self.B)

        if self.initial_mass is None:
            # 
            self.initial_mass = total_mass
            self.mass_history = [total_mass]
        else:
            self.mass_history.append(total_mass)

            # 
            if abs(self.initial_mass) > 1e-14:
                mass_error = abs(total_mass - self.initial_mass) / self.initial_mass * 100

                # 1%
                if mass_error > 1.0:
                    print(f"[WARN]   {mass_error:.2f}%  t={self.t:.4f}s")

    def get_statistics(self) -> Dict:
        """
        

        Returns:
            dict: 
        """
        # Phase 8.1
        stats = super().get_statistics()

        # Phase 8.2
        stats['wd_activations'] = self.wd_activations

        if self.step_count > 0:
            stats['interface_flux_usage_rate'] = self.wd_activations / self.step_count
        else:
            stats['interface_flux_usage_rate'] = 0.0

        stats['interface_type_counts'] = self.interface_type_counts.copy()

        # 
        if self.initial_mass is not None and abs(self.initial_mass) > 1e-14:
            current_mass = np.sum(self.h * self.dx * self.B)
            stats['mass_conservation_error'] = abs(current_mass - self.initial_mass) / self.initial_mass * 100
        else:
            stats['mass_conservation_error'] = 0.0

        stats['mass_history'] = self.mass_history.copy() if self.mass_history else []

        return stats

    def print_statistics(self):
        """"""
        stats = self.get_statistics()

        print(f"\n{'='*70}")
        print("WENO3")
        print(f"{'='*70}")

        # Phase 8.1
        print("\n[Phase 8.1]")
        print(f": {stats['total_steps']}")
        print(f": {stats['pp_activations']}")
        print(f": {stats['activation_rate']*100:.2f}%")

        if stats['pp_activations'] > 0:
            print(f"θ: {stats['min_theta']:.6f}")
            print(f"θ: {stats['avg_theta']:.6f}")

        # Phase 8.2
        print("\n[Phase 8.2]")
        print(f": {stats['wd_activations']}")
        print(f": {stats['interface_flux_usage_rate']*100:.2f}%")

        print("\n:")
        total_interfaces = sum(stats['interface_type_counts'].values())
        if total_interfaces > 0:
            for itype, count in stats['interface_type_counts'].items():
                percentage = count / total_interfaces * 100
                print(f"  - {itype}: {count} ({percentage:.1f}%)")
        else:
            print("  ")

        print(f"\n: {stats['mass_conservation_error']:.4f}%")

        print(f"\n{'='*70}")
        print(":")
        print("- θ=1.0: WENO3")
        print("- θ∈(0,1): ")
        print("- θ=0.0: ")
        print("- : ")
        print(f"{'='*70}\n")


# =============================================================================
# 
# =============================================================================

def quick_test():
    """
    WENO3

    RP5
    """
    print("\n" + "="*80)
    print("WENO3Phase 8.2")
    print("="*80)

    # 
    L = 100.0
    B = 10.0
    x_dam = L / 2.0
    n_cells = 200  # 
    t_end = 0.2  # 

    # RP5
    h_L, u_L = 0.0, 0.0
    h_R, u_R = 2.0, 0.0  # 

    print(f"\nRP5:")
    print(f"- : h={h_L}, u={u_L} ()")
    print(f"- : h={h_R}, u={u_R} ()")
    print(f"- : {n_cells} cells")
    print(f"- : {t_end}s")

    # 
    solver = WetDryEnhancedWENO3(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        cfl=0.2,
        eps_pp=1e-10,
        theta_min=0.0,
        wet_dry_threshold=1e-4,
        interface_theta_max=0.3,
        use_pp=True,
        use_wd_flux=True,
        use_enhanced_bc=True,
        well_balanced=False,
        use_numba=False
    )

    # 
    x = solver.x
    h_init = np.where(x <= x_dam, h_L, h_R)
    Q_init = B * np.where(x <= x_dam, h_L * u_L, h_R * u_R)

    bc_left = {'type': 'transmissive'}
    bc_right = {'type': 'transmissive'}
    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 
    print(f"\n...")
    step_count = 0

    while solver.t < t_end:
        solver.step()
        step_count += 1

        if step_count % 20 == 0:
            h_min = np.min(solver.h)
            h_max = np.max(solver.h)
            print(f"  Step {step_count}: t={solver.t:.4f}s, h∈[{h_min:.4f}, {h_max:.4f}]")

    print(f"\n: {step_count}, : t={solver.t:.4f}s")

    # 
    solver.print_statistics()

    # 
    h_min = np.min(solver.h)
    print(f"\n:")
    print(f"- : {h_min:.6e}")
    if h_min >= 0.0:
        print("-  h≥0")
    else:
        print(f"-  h<0")

    # 
    stats = solver.get_statistics()
    mass_error = stats['mass_conservation_error']
    print(f"\n:")
    print(f"- : {mass_error:.4f}%")
    if mass_error < 0.1:
        print("-  <0.1%")
    elif mass_error < 1.0:
        print("- [WARN]  <1.0%")
    else:
        print("-  >1.0%")

    print("\n" + "="*80)
    print("")
    print("="*80)

    return solver


if __name__ == '__main__':
    # 
    solver = quick_test()
