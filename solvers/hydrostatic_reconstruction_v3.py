"""
 v3 - 

ghost cells


1. Periodic
2. Reflective/Wall
3. Extrapolation
"""

import numpy as np
from typing import Tuple, Optional
import math
from enum import Enum


class BoundaryType(Enum):
    """"""
    PERIODIC = "periodic"          # 
    REFLECTIVE = "reflective"      # 
    EXTRAPOLATION = "extrapolation"  # 
    TRANSMISSIVE = "transmissive"  # 


class WellBalancedSolverV3:
    """
     v3 - 

    
    1. ghost cells
    2. 
    3. 
    """

    def __init__(self,
                 g: float = 9.81,
                 eps_dry: float = 1e-6,
                 bc_left: BoundaryType = BoundaryType.TRANSMISSIVE,
                 bc_right: BoundaryType = BoundaryType.TRANSMISSIVE):
        """
        

        :
            g: 
            eps_dry: 
            bc_left: 
            bc_right: 
        """
        self.g = g
        self.eps_dry = eps_dry
        self.bc_left = bc_left
        self.bc_right = bc_right

    def setup_ghost_cells(
        self,
        h: np.ndarray,
        hu: np.ndarray,
        z: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        

        :
            h, hu, z:  [n_cells]

        :
            h_ext, hu_ext, z_ext:  [n_cells+2]
        """
        n_cells = len(h)

        # 1
        h_ext = np.zeros(n_cells + 2)
        hu_ext = np.zeros(n_cells + 2)
        z_ext = np.zeros(n_cells + 2)

        # 
        h_ext[1:-1] = h
        hu_ext[1:-1] = hu
        z_ext[1:-1] = z

        # 0
        if self.bc_left == BoundaryType.TRANSMISSIVE:
            # 
            eta_0 = h[0] + z[0]
            z_ext[0] = z[0]  # 
            h_ext[0] = eta_0 - z_ext[0]
            hu_ext[0] = hu[0]

        elif self.bc_left == BoundaryType.REFLECTIVE:
            # 
            h_ext[0] = h[0]
            hu_ext[0] = -hu[0]  # 
            z_ext[0] = z[0]

        elif self.bc_left == BoundaryType.EXTRAPOLATION:
            # 
            h_ext[0] = h[0]
            hu_ext[0] = hu[0]
            z_ext[0] = z[0]

        # n_cells+1
        if self.bc_right == BoundaryType.TRANSMISSIVE:
            # 
            eta_n = h[-1] + z[-1]
            z_ext[-1] = z[-1]  # 
            h_ext[-1] = eta_n - z_ext[-1]
            hu_ext[-1] = hu[-1]

        elif self.bc_right == BoundaryType.REFLECTIVE:
            # 
            h_ext[-1] = h[-1]
            hu_ext[-1] = -hu[-1]
            z_ext[-1] = z[-1]

        elif self.bc_right == BoundaryType.EXTRAPOLATION:
            # 
            h_ext[-1] = h[-1]
            hu_ext[-1] = hu[-1]
            z_ext[-1] = z[-1]

        return h_ext, hu_ext, z_ext

    def reconstruct_interface(
        self, h_L: float, z_L: float, h_R: float, z_R: float
    ) -> Tuple[float, float]:
        """"""
        eta_L = h_L + z_L
        eta_R = h_R + z_R
        z_interface = max(z_L, z_R)

        h_star_L = max(0.0, eta_L - z_interface)
        h_star_R = max(0.0, eta_R - z_interface)

        return h_star_L, h_star_R

    def hll_flux(
        self, h_L: float, hu_L: float, h_R: float, hu_R: float
    ) -> Tuple[float, float]:
        """HLL Riemann"""
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        u_L = hu_L / h_L if h_L > self.eps_dry else 0.0
        u_R = hu_R / h_R if h_R > self.eps_dry else 0.0

        c_L = math.sqrt(self.g * h_L) if h_L > self.eps_dry else 0.0
        c_R = math.sqrt(self.g * h_R) if h_R > self.eps_dry else 0.0

        s_L = min(u_L - c_L, u_R - c_R)
        s_R = max(u_L + c_L, u_R + c_R)

        if abs(s_L) < 1e-14 and abs(s_R) < 1e-14:
            s_L = -1e-10
            s_R = 1e-10

        if h_L > self.eps_dry:
            F_mass_L = hu_L
            F_mom_L = hu_L * u_L + 0.5 * self.g * h_L**2
        else:
            F_mass_L = 0.0
            F_mom_L = 0.0

        if h_R > self.eps_dry:
            F_mass_R = hu_R
            F_mom_R = hu_R * u_R + 0.5 * self.g * h_R**2
        else:
            F_mass_R = 0.0
            F_mom_R = 0.0

        if s_L >= 0:
            return F_mass_L, F_mom_L
        elif s_R <= 0:
            return F_mass_R, F_mom_R
        else:
            U_L = [h_L, hu_L]
            U_R = [h_R, hu_R]
            F_L = [F_mass_L, F_mom_L]
            F_R = [F_mass_R, F_mom_R]

            F_mass_HLL = (s_R * F_L[0] - s_L * F_R[0] +
                         s_L * s_R * (U_R[0] - U_L[0])) / (s_R - s_L)
            F_mom_HLL = (s_R * F_L[1] - s_L * F_R[1] +
                        s_L * s_R * (U_R[1] - U_L[1])) / (s_R - s_L)

            return F_mass_HLL, F_mom_HLL

    def solve_step(
        self,
        h: np.ndarray,
        hu: np.ndarray,
        z: np.ndarray,
        dx: float,
        n: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        

        :
            (F_mass, F_momentum, S_mass, S_momentum)
        """
        n_cells = len(h)

        # Step 1: 
        h_ext, hu_ext, z_ext = self.setup_ghost_cells(h, hu, z)

        # n_cells+1
        F_mass = np.zeros(n_cells + 1)
        F_momentum = np.zeros(n_cells + 1)

        # 
        # h_star[i] = (, ) i
        h_star_interfaces = np.zeros((n_cells + 1, 2))

        # Step 2: 
        for i in range(n_cells + 1):
            # iii+1
            # 00n_cellsn_cells-1

            h_L = h_ext[i]
            hu_L = hu_ext[i]
            z_L = z_ext[i]

            h_R = h_ext[i+1]
            hu_R = hu_ext[i+1]
            z_R = z_ext[i+1]

            # 
            h_star_L, h_star_R = self.reconstruct_interface(h_L, z_L, h_R, z_R)
            h_star_interfaces[i, 0] = h_star_L
            h_star_interfaces[i, 1] = h_star_R

            # 
            if h_L > self.eps_dry:
                hu_star_L = hu_L * (h_star_L / h_L)
            else:
                hu_star_L = 0.0

            if h_R > self.eps_dry:
                hu_star_R = hu_R * (h_star_R / h_R)
            else:
                hu_star_R = 0.0

            # HLL
            F_mass[i], F_momentum[i] = self.hll_flux(
                h_star_L, hu_star_L, h_star_R, hu_star_R
            )

        # Step 3: 
        S_mass = np.zeros(n_cells)
        S_momentum = np.zeros(n_cells)

        for i in range(n_cells):
            # iii+1

            # i
            h_star_L = h_star_interfaces[i, 1]

            # i
            h_star_R = h_star_interfaces[i+1, 0]

            # Audusse
            # S = g/2 * (h*_{i+1/2}² - h*_{i-1/2}²) / dx
            # 
            S_gravity = 0.5 * self.g * (h_star_R**2 - h_star_L**2) / dx

            # 
            if h[i] > self.eps_dry and abs(n) > 1e-10:
                u_i = hu[i] / h[i]
                R_i = h[i]
                S_friction = -self.g * n**2 * abs(u_i) * hu[i] / (R_i**(4/3))
            else:
                S_friction = 0.0

            S_mass[i] = 0.0
            S_momentum[i] = S_gravity + S_friction

        return F_mass, F_momentum, S_mass, S_momentum


def test_well_balanced_v3():
    """v3"""
    print("=" * 70)
    print(" v3")
    print("=" * 70)

    # 
    solver = WellBalancedSolverV3(
        g=9.81,
        bc_left=BoundaryType.TRANSMISSIVE,
        bc_right=BoundaryType.TRANSMISSIVE
    )

    # 1: 
    print("\n1: ")
    print("-" * 70)

    n_cells = 10
    dx = 1.0
    z = np.zeros(n_cells)
    h = 10.0 * np.ones(n_cells)
    hu = np.zeros(n_cells)

    print(f"z=0, h=10m, u=0")

    F_mass, F_momentum, S_mass, S_momentum = solver.solve_step(h, hu, z, dx, n=0.0)

    # 
    R_mass = np.zeros(n_cells)
    R_momentum = np.zeros(n_cells)

    for i in range(n_cells):
        dF_mass = -(F_mass[i+1] - F_mass[i]) / dx
        dF_momentum = -(F_momentum[i+1] - F_momentum[i]) / dx
        R_mass[i] = dF_mass + S_mass[i]
        R_momentum[i] = dF_momentum + S_momentum[i]

    max_R_mass = np.max(np.abs(R_mass))
    max_R_momentum = np.max(np.abs(R_momentum))

    print(f"")
    print(f"  max={max_R_mass:.2e}")
    print(f"  max={max_R_momentum:.2e}")

    test1_pass = max_R_mass < 1e-10 and max_R_momentum < 1e-10
    print(f"{'[OK][OK][OK] PASS' if test1_pass else '[FAIL][FAIL][FAIL] FAIL'}")

    # 2: 
    print("\n2: ")
    print("-" * 70)

    n_cells = 10
    dx = 1.0
    x = np.linspace(0.5*dx, 10-0.5*dx, n_cells)
    z = np.zeros(n_cells)

    # 
    for i in range(n_cells):
        if x[i] < 2.0:
            z[i] = 0.0
        elif x[i] < 3.0:
            z[i] = 1.5  # 
        elif x[i] < 5.0:
            z[i] = 1.5 + 0.5 * (x[i] - 3.0)  # 
        elif x[i] < 7.0:
            z[i] = 2.5  # 
        elif x[i] < 8.0:
            z[i] = 2.5 - 1.0 * (x[i] - 7.0)  # 
        else:
            z[i] = 1.5

    # 
    eta_const = 10.0
    h = eta_const - z
    hu = np.zeros(n_cells)

    print(f"z: {z.min():.1f}-{z.max():.1f}mη=10mu=0")

    F_mass, F_momentum, S_mass, S_momentum = solver.solve_step(h, hu, z, dx, n=0.0)

    # 
    R_mass = np.zeros(n_cells)
    R_momentum = np.zeros(n_cells)

    for i in range(n_cells):
        dF_mass = -(F_mass[i+1] - F_mass[i]) / dx
        dF_momentum = -(F_momentum[i+1] - F_momentum[i]) / dx
        R_mass[i] = dF_mass + S_mass[i]
        R_momentum[i] = dF_momentum + S_momentum[i]

    max_R_mass = np.max(np.abs(R_mass))
    max_R_momentum = np.max(np.abs(R_momentum))
    rms_R_momentum = np.sqrt(np.mean(R_momentum**2))

    print(f"")
    print(f"  max={max_R_mass:.2e}")
    print(f"  max={max_R_momentum:.2e}, RMS={rms_R_momentum:.2e}")

    test2_pass = max_R_mass < 1e-10 and max_R_momentum < 1e-10

    if not test2_pass:
        # 
        i_max = np.argmax(np.abs(R_momentum))
        print(f"\n{i_max}")
        print(f"  h={h[i_max]:.3f}, z={z[i_max]:.3f}, η={h[i_max]+z[i_max]:.3f}")
        print(f"  F_L={F_momentum[i_max]:.3f}, F_R={F_momentum[i_max+1]:.3f}")
        print(f"  ∂F/∂x={-(F_momentum[i_max+1]-F_momentum[i_max])/dx:.3f}")
        print(f"  S={S_momentum[i_max]:.3f}")
        print(f"  R={R_momentum[i_max]:.3f}")

    print(f"{'[OK][OK][OK] PASS' if test2_pass else '[FAIL][FAIL][FAIL] FAIL'}")

    # 
    print("\n" + "=" * 70)
    overall_pass = test1_pass and test2_pass
    if overall_pass:
        print("[OK][OK][OK] ")
    else:
        print("")
    print("=" * 70)

    return overall_pass


if __name__ == "__main__":
    import sys
    success = test_well_balanced_v3()
    sys.exit(0 if success else 1)
