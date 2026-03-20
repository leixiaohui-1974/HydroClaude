#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov


1.  FVM- 
2.  HLL Riemann - 
3.  TVD-RK2  - +
4.  Minmod - +

1D

: Toro (2009) "Riemann Solvers and Numerical Methods for Fluid Dynamics"

: HydroClaude Team
: 2025-10-29
"""

import numpy as np
from typing import Tuple, Dict, Optional

# 
from .boundary_conditions import CharacteristicBC

# 
from physics.cross_section import CrossSection, RectangularSection, SectionType

# Numba
try:
    from .riemann_numba import (
        hll_flux_numba,
        muscl_reconstruction_numba,
        compute_all_fluxes_numba,
        compute_spatial_derivatives_numba
    )
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

# HLLC RiemannPhase 9.2
try:
    from .riemann_hllc import (
        hllc_flux_numba,
        compute_all_hllc_fluxes_numba
    )
    HLLC_AVAILABLE = True
except ImportError:
    HLLC_AVAILABLE = False

# RiemannPhase 9.3
try:
    from .riemann_exact import (
        exact_riemann_flux_numba,
        exact_riemann_flux
    )
    EXACT_AVAILABLE = True
except ImportError:
    EXACT_AVAILABLE = False

# Numba JITPhase 6.5
try:
    from .numba_kernels import (
        hll_flux_kernel,
        entropy_fix_kernel,
        compute_source_term_kernel,
        compute_friction_slope
    )
    NUMBA_KERNELS_AVAILABLE = True
except ImportError:
    NUMBA_KERNELS_AVAILABLE = False


class GodunvFVMSolver:
    """
    Godunov
    
    Saint-Venant:
    ∂U/∂t + ∂F/∂x = S
    
    :
    U = [h, Q]^T  ()
    F = [Q, Q²/A + 0.5*g*h²*B]^T  ()
    S = [0, g*A*(S0 - Sf)]^T  ()
    
    :
    dU_i/dt = -1/dx * (F_{i+1/2} - F_{i-1/2}) + S_i
    
     F_{i+1/2} HLL Riemann
    """
    
    def __init__(
        self,
        width: float,
        length: float,
        n_cells: int,
        manning_n: float,
        slope: float = None,
        z_b: np.ndarray = None,
        g: float = 9.81,
        cfl: float = 0.5,
        eps_dry: float = 1e-4,
        order: int = 2,
        riemann_solver: str = 'hll',
        well_balanced: bool = False,
        use_numba: bool = True,
        source_term_method: str = 'standard',
        source_term_treatment: str = 'coupled',
        dt_max: float = None,
        entropy_fix: bool = False,
        critical_flow_treatment: bool = False,
        cross_section: Optional[CrossSection] = None
    ):
        """
        

        Args:
            width:  (m)
            length:  (m)
            n_cells: 
            manning_n: Manning
            slope:  (z_b)
            z_b:  (slopeWell-Balanced)
            g: 
            cfl: CFL (0.5-0.8)
            eps_dry: 
            order:  (1=, 2=MUSCL)
            riemann_solver: Riemann ('hll'  'hllc')
                          'hll'
                          'hllc'
            well_balanced: well-balanced (False)
                          Truehydrostatic reconstruction
            use_numba: Numba JIT (True)
                      True10-50
            source_term_method:  ('standard'  'interface')
                              'standard':  S = g*A*(S0 - Sf)
                              'interface': Zhou's Surface Gradient Method
                                         
            source_term_treatment:  ('coupled'  'strang_splitting')
                                 'coupled': TVD-RK2
                                 'strang_splitting': Strang
                                                    (dt/2) → (dt) → (dt/2)
                                                    -
            dt_max:  ()
                   None
                   
                   0.5-1.0s
            entropy_fix: Harten-Hyman entropy (False)
                        Trueentropy
            critical_flow_treatment:  (False)
                                   True(0.9<Fr<1.1)
            cross_section:  ()
                         NoneRectangularSection(width)
                         TrapezoidalSection, CompoundSection, NaturalSection
        """
        # 
        if cross_section is None:
            # 
            self.cross_section = RectangularSection("default", width)
        else:
            self.cross_section = cross_section
            # [WARN]  Phase 2.3
            #
            # 1.  A, P, R
            # 2.  A
            # 3.  Froude
            #
            #
            # 1. [WARN]   (0.5*g*h²*B) -
            # 2. [WARN]   -
            # 3. [WARN]   (CharacteristicBC) -
            #
            # //
            # -
            # -
            # - Froude
            # - [WARN]
            #
            #
            #       /
            if cross_section.section_type != SectionType.RECTANGULAR:
                import warnings
                warnings.warn(
                    "非矩形断面支持：部分実現 (Phase 2.3)\n"
                    "[WARN]   (Phase 2.3)\n"
                    "Froude\n"
                    "\n"
                    "\n"
                    ": docs/STAGE2_PHASE2_3_COMPLETION_REPORT.md",
                    UserWarning
                )

        # self.B ()
        self.B = width
        self.L = length
        self.n_cells = n_cells
        self.dx = length / n_cells
        self.n = manning_n

        # slopez_b
        if slope is None and z_b is None:
            raise ValueError("slopez_b")
        if slope is not None and z_b is not None:
            raise ValueError("slopez_b")

        if slope is not None:
            # 
            if isinstance(slope, (int, float)):
                self.S0 = np.ones(n_cells) * slope
            else:
                self.S0 = np.asarray(slope)
                if len(self.S0) != n_cells:
                    raise ValueError(f"slope({len(self.S0)})({n_cells})")
        else:
            # Well-Balanced
            self.z_b = np.asarray(z_b)
            if len(self.z_b) != n_cells:
                raise ValueError(f"z_b({len(self.z_b)})({n_cells})")
            # S0
            self.S0 = np.zeros(n_cells)
            for i in range(n_cells):
                if i == 0:
                    self.S0[i] = self.z_b[i] / (self.dx * 0.5) if self.dx > 0 else 0
                else:
                    self.S0[i] = (self.z_b[i] - self.z_b[i-1]) / self.dx

        self.g = g
        self.cfl = cfl
        self.dt_max = dt_max
        self.eps_dry = eps_dry
        self.order = order
        self.riemann_solver = riemann_solver.lower()
        self.well_balanced = well_balanced
        self.source_term_method = source_term_method.lower()
        self.source_term_treatment = source_term_treatment.lower()
        self.entropy_fix = entropy_fix
        self.critical_flow_treatment = critical_flow_treatment

        # source_term_method
        if self.source_term_method not in ['standard', 'interface']:
            raise ValueError(f"source_term_method'standard''interface': {source_term_method}")

        # source_term_treatment
        if self.source_term_treatment not in ['coupled', 'strang_splitting']:
            raise ValueError(f"source_term_treatment'coupled''strang_splitting': {source_term_treatment}")

        # [WARN] Interface2025-10-29
        if self.source_term_method == 'interface':
            raise NotImplementedError(
                "\n" + "="*80 + "\n"
                " Interface Source Method\n"
                "="*80 + "\n"
                ": 61% → 114%\n"
                "\n"
                "MacDonald:\n"
                "  - Standard:  61.41%\n"
                "  - Interface:  114.17%  52.76%\n"
                "\n"
                ":\n"
                "  Zhou's Surface Gradient Method:\n"
                "  1.  η = h + z_b (NOT IMPLEMENTED)\n"
                "  2. η h_L, h_R (NOT IMPLEMENTED)\n"
                "  3.  (INCORRECTLY IMPLEMENTED)\n"
                "\n"
                "3\n"
                "\n"
                ":\n"
                "  - _compute_rhsreconstruction\n"
                "  - η\n"
                "  - \n"
                "\n"
                ":  source_term_method='standard'\n"
                ": Zhou's SGM\n"
                "\n"
                ":\n"
                "  - docs/INTERFACE_SOURCE_METHOD_FAILURE_ANALYSIS.md\n"
                "  - Zhou et al. (2001) JCP 168(1):1-25\n"
                "="*80
            )

        # Numba
        self.use_numba = use_numba and NUMBA_AVAILABLE
        if use_numba and not NUMBA_AVAILABLE:
            print("  [WARN]  NumbaPython")

        if self.riemann_solver not in ['hll', 'hllc', 'exact']:
            raise ValueError(f"Riemann'hll', 'hllc''exact': {riemann_solver}")

        # Phase 9.2: HLLC - EXPERIMENTAL, NOT PRODUCTION READY
        # [WARN]  WARNING: HLLC
        # - Dam Breakt=1.69sNaN
        # - 
        # - Lake at RestHLL141%
        # : docs/PHASE_9_2_CRITICAL_FINDINGS.md
        # : HLL ()
        if self.riemann_solver == 'hllc':
            if not HLLC_AVAILABLE:
                raise ImportError(
                    "HLLCriemann_hllc\n"
                    "solvers/riemann_hllc.py"
                )

            # 
            import warnings
            warnings.warn(
                "\n" + "="*80 + "\n"
                "[WARN][WARN][WARN]  HLLC - NOT PRODUCTION READY  [WARN][WARN][WARN]\n"
                "="*80 + "\n"
                "HLLC:\n"
                "  - Dam Breakt=1.69sNaN\n"
                "  - 10^75\n"
                "  - Lake at RestHLL141%\n"
                "\n"
                "[WARN]  :\n"
                "  -  riemann_solver='hll' ()\n"
                "  - HLLC\n"
                "\n"
                ": docs/PHASE_9_2_CRITICAL_FINDINGS.md\n"
                "="*80 + "\n",
                UserWarning,
                stacklevel=2
            )

        # Phase 9.3: Riemann -  DO NOT USE 
        # [WARN][WARN][WARN] :  (42%)
        # [WARN][WARN][WARN] , 
        #  : bug
        if self.riemann_solver == 'exact':
            if not EXACT_AVAILABLE:
                raise ImportError(
                    "riemann_exact\n"
                    "solvers/riemann_exact.py"
                )

            #   
            import warnings
            warnings.warn(
                "\n" + "="*80 + "\n"
                "   - DO NOT USE  \n"
                "="*80 + "\n"
                "Riemann:\n"
                "  -  (1042%)\n"
                "  - 2m14.5m ()\n"
                "  - Well-Balancedt=0.3s\n"
                "  - bug\n"
                "\n"
                " :\n"
                "  - \n"
                "  -  riemann_solver='hll' ()\n"
                "  - \n"
                "\n"
                ": docs/PHASE_9_3_EXACT_RIEMANN_SOLVER.md\n"
                ": tests/diagnose_exact_mass_loss.py\n"
                "="*80 + "\n",
                UserWarning,
                stacklevel=2
            )

            print("[WARN]  Riemann (Phase 9.3) - ")
            print("    : ")
            print("    ")
            print("    : riemann_solver='hll'\n")

        # 
        self.h = np.zeros(n_cells)  # 
        self.Q = np.zeros(n_cells)  # 

        # 
        self.x = np.linspace(0.5*self.dx, length - 0.5*self.dx, n_cells)

        # well-balanced
        # z_bS0
        if slope is not None:
            # x=0z_b(x) = z_0 - ∫S0(ξ)dξ
            # 0
            self.z_b = np.zeros(n_cells)
            for i in range(n_cells):
                if i == 0:
                    self.z_b[i] = self.S0[i] * self.x[i]  # x=0x[0]
                else:
                    # 
                    self.z_b[i] = self.z_b[i-1] + 0.5 * (self.S0[i-1] + self.S0[i]) * self.dx
        # else: z_b

        # 
        z_b_range = np.max(self.z_b) - np.min(self.z_b)
        has_variable_bottom = z_b_range > 1e-10  #  > 0.1mm

        # WARNING: well-balanced
        if has_variable_bottom and not self.well_balanced:
            import warnings
            warnings.warn(
                "\n" + "="*80 + "\n"
                "[WARN]  Well-Balanced\n"
                "="*80 + "\n"
                f": {np.min(self.z_b):.2f} ~ {np.max(self.z_b):.2f} m "
                f"( {z_b_range:.2f} m)\n"
                ": well_balanced=False\n"
                "\n"
                "Lake at Rest P0:\n"
                "  - 2m:  3.99 m \n"
                "  - 5m:  11.35 m \n"
                "  - : 0.01% ~ 2%\n"
                "\n"
                ":\n"
                "  1. \n"
                "  2. \n"
                "  3. \n"
                "\n"
                ":\n"
                "  1.  well_balanced=True\n"
                "     Hydrostatic Reconstruction - \n"
                "  2. < 0.001\n"
                "  3. /\n"
                "\n"
                ":\n"
                "  - LAKE_AT_REST_TEST_REPORT.md ()\n"
                "  - DEVELOPMENT_STANDARDS.md ()\n"
                "="*80,
                UserWarning,
                stacklevel=2
            )

        # 
        self.t = 0.0
        self.dt = 0.0

        # 
        self.bc_left = None
        self.bc_right = None

        # 
        self.characteristic_bc = CharacteristicBC(g=g)

        # 
        self.initial_mass = 0.0
        self.step_count = 0
        
        # 禁用打印以避免Windows编码问题
        # print(f"Godunov-FVM:")
        # print(f"  : {n_cells}")
        # print(f"  dx = {self.dx:.3f} m")
        # print(f"  : {order}")
        # print(f"  : TVD-RK2")
        # print(f"  Riemann: {self.riemann_solver.upper()}")
        # if self.well_balanced:
        #     print(f"  Well-Balanced:  (Hydrostatic Reconstruction)")
        # if self.entropy_fix:
        #     print(f"  Entropy Fix:  (Harten-Hyman)")
        # if self.critical_flow_treatment:
        #     print(f"  Critical Flow Treatment:  (Lax-Friedrichs)")
        # if self.use_numba:
        #     print(f"  [JIT] Numba JIT: Enabled (High Performance Mode)")
    
    def initialize(
        self,
        h_init: np.ndarray,
        Q_init: np.ndarray,
        bc_left: Dict,
        bc_right: Dict
    ):
        """"""
        self.h = h_init.copy()
        self.Q = Q_init.copy()
        self.bc_left = bc_left
        self.bc_right = bc_right
        self.t = 0.0  # 

        # 
        self.last_F_h = None  #  [n+1]
        self.last_F_Q = None  #  [n+1]

        # 
        self.initial_mass = self._compute_total_mass(exclude_boundary_cells=False)

        # print(f"  : {self.initial_mass:.2f} m³")  # Disabled for Windows compatibility
    
    def compute_dt(self) -> float:
        """
        CFL

        Returns:
            dt: dt_max
        """
        lambda_max = 0.0

        # 
        for i in range(self.n_cells):
            if self.h[i] > self.eps_dry:
                # u+c
                A = self.h[i] * self.B
                u = self.Q[i] / A
                c = np.sqrt(self.g * self.h[i])
                speed = abs(u) + c
                lambda_max = max(lambda_max, speed)
            else:
                # cell
                c_neighbor = 0.0
                if i > 0 and self.h[i-1] > self.eps_dry:
                    c_neighbor = max(c_neighbor, np.sqrt(self.g * self.h[i-1]))
                if i < self.n_cells-1 and self.h[i+1] > self.eps_dry:
                    c_neighbor = max(c_neighbor, np.sqrt(self.g * self.h[i+1]))
                lambda_max = max(lambda_max, c_neighbor)

        # Ensure lambda_max is never zero to avoid division by zero
        lambda_max = max(lambda_max, 1e-8)

        dt = self.cfl * self.dx / lambda_max

        # Maximum time step cap to prevent huge dt when domain is completely dry
        dt = min(dt, 1.0)

        # dt_max
        if self.dt_max is not None:
            dt = min(dt, self.dt_max)

        return dt
    
    def step(self, dt: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        source_term_treatment
        - 'coupled': TVD-RK2
        - 'strang_splitting': Strang
        """
        if dt is None:
            dt = self.compute_dt()

        self.dt = dt

        # 
        if self.source_term_treatment == 'strang_splitting':
            self._step_strang_splitting(dt)
        else:  # coupled
            self._step_coupled_rk2(dt)

        self.t += dt
        self.step_count += 1

        return self.h.copy(), self.Q.copy()

    def _step_coupled_rk2(self, dt: float):
        """
        TVD-RK2

        RK2 (Heun's method):
        1. U* = U^n + dt * L(U^n)
        2. U^{n+1} = 0.5*(U^n + U*) + 0.5*dt*L(U*)

         L(U) = -1/dx*(F_{i+1/2} - F_{i-1/2}) + S
        """
        # 
        h_n = self.h.copy()
        Q_n = self.Q.copy()

        # === 1 ===
        dh_dt, dQ_dt = self._compute_rhs(h_n, Q_n)
        h_star = h_n + dt * dh_dt
        Q_star = Q_n + dt * dQ_dt

        # 
        # h_star, Q_star = self._apply_bc(h_star, Q_star)

        #
        h_star = np.maximum(h_star, 0.0)
        Q_star[h_star < self.eps_dry] = 0.0

        # === 2 ===
        dh_dt_star, dQ_dt_star = self._compute_rhs(h_star, Q_star)
        self.h = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt_star
        self.Q = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt_star

        #
        self.h, self.Q = self._apply_bc(self.h, self.Q)

        #
        self.h = np.maximum(self.h, 0.0)
        self.Q[self.h < self.eps_dry] = 0.0

    def _step_strang_splitting(self, dt: float):
        """
        Strang

        
        1. (dt/2): dU/dt = -∂F/∂x
        2. (dt):   dU/dt = S
        3. (dt/2): dU/dt = -∂F/∂x

        
        """
        # 
        h_n = self.h.copy()
        Q_n = self.Q.copy()

        # === 1 dt/2 ===
        # RHS
        dh_dt, dQ_dt = self._compute_flux_only_rhs(h_n, Q_n)
        h_half = h_n + 0.5 * dt * dh_dt
        Q_half = Q_n + 0.5 * dt * dQ_dt

        # 
        h_half, Q_half = self._apply_bc(h_half, Q_half)
        h_half = np.maximum(h_half, 0.0)

        # === 2 dt ===
        # dU/dt = Stt+dt
        h_source, Q_source = self._solve_source_ode(h_half, Q_half, dt)

        # 
        h_source, Q_source = self._apply_bc(h_source, Q_source)
        h_source = np.maximum(h_source, 0.0)

        # === 3 dt/2 ===
        dh_dt, dQ_dt = self._compute_flux_only_rhs(h_source, Q_source)
        self.h = h_source + 0.5 * dt * dh_dt
        self.Q = Q_source + 0.5 * dt * dQ_dt

        #
        self.h, self.Q = self._apply_bc(self.h, self.Q)
        self.h = np.maximum(self.h, 0.0)
        self.Q[self.h < self.eps_dry] = 0.0

    def _compute_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        +

        dU/dt = L(U) = -1/dx*(F_{i+1/2} - F_{i-1/2}) + S

        Returns:
            dh/dt, dQ/dt
        """
        # DEBUG flag for diagnostics
        DEBUG = False  # Set to False to disable debug output

        n = len(h)

        # DEBUG: Check actual eta values at start
        if DEBUG and self.t < 1e-6:
            eta = h + self.z_b
            print(f"\n[DEBUG] At start of _compute_rhs:")
            print(f"  eta range: {np.min(eta):.6f} ~ {np.max(eta):.6f}")
            print(f"  eta[39:42]: {eta[39:42]}")
            print(f"  z_b[39:42]: {self.z_b[39:42]}")
            print(f"  h[39:42]: {h[39:42]}")

        # 
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)
        
        # ghost cells
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)

        # Well-balanced:  η = h + z_b
        if self.well_balanced:
            # cell centers
            eta = h + self.z_b

            # etaghost cells
            eta_ext = np.zeros(n + 2)
            eta_ext[1:n+1] = eta

            # ghosteta h_bc + z_b_ghost
            # Lake at Restetaghosteta
            if self.bc_left['type'] == 'h':
                # Ghost cell z_b: extrapolate to the left of the domain
                # z_b_ghost = 2*z_b[0] - z_b[1] (linear extrapolation)
                value = self.bc_left['value']
                h_bc = value if not callable(value) else value(self.t)
                z_b_ghost = (2.0 * self.z_b[0] - self.z_b[1]) if n > 1 else self.z_b[0]
                eta_bc = h_bc + z_b_ghost
                # Lake at Resteta
                eta_ext[0] = eta_bc
            else:  # Q boundary
                # eta
                eta_ext[0] = eta[0]

            # ghosteta
            if self.bc_right['type'] == 'h':
                # Ghost cell z_b: extrapolate to the right of the domain
                # z_b_ghost = 2*z_b[n-1] - z_b[n-2] (linear extrapolation)
                value = self.bc_right['value']
                h_bc = value if not callable(value) else value(self.t)
                z_b_ghost = (2.0 * self.z_b[n-1] - self.z_b[n-2]) if n > 1 else self.z_b[n-1]
                eta_bc = h_bc + z_b_ghost
                # Lake at Resteta
                eta_ext[n+1] = eta_bc
            else:  # Q boundary
                eta_ext[n+1] = eta[n-1]

            # 
            if self.order == 2:
                eta_L, eta_R = self._muscl_reconstruction(eta_ext)
            else:
                eta_L = eta_ext[:-1]
                eta_R = eta_ext[1:]

            # 
            # z_b
            z_b_ext = np.zeros(n + 2)
            z_b_ext[1:n+1] = self.z_b
            # ghost: 
            z_b_ext[0] = self.z_b[0] - (self.z_b[1] - self.z_b[0]) if n > 1 else self.z_b[0]
            # ghost: 
            z_b_ext[n+1] = self.z_b[n-1] + (self.z_b[n-1] - self.z_b[n-2]) if n > 1 else self.z_b[n-1]

            # Audusse et al. 2004
            z_b_interface = np.maximum(z_b_ext[:-1], z_b_ext[1:])

            # hydrostatic reconstruction
            h_L = np.maximum(0.0, eta_L - z_b_interface)
            h_R = np.maximum(0.0, eta_R - z_b_interface)

            # DEBUG: Print reconstruction details
            if DEBUG and self.t < 1e-6:
                print(f"\n[DEBUG] Hydrostatic Reconstruction:")
                print(f"  eta_L[40:45]: {eta_L[40:45]}")
                print(f"  eta_R[40:45]: {eta_R[40:45]}")
                print(f"  z_b_interface[40:45]: {z_b_interface[40:45]}")
                print(f"  h_L[40:45] (after reconstruction): {h_L[40:45]}")
                print(f"  h_R[40:45] (after reconstruction): {h_R[40:45]}")
                print(f"  h_L - h_R [40:45]: {h_L[40:45] - h_R[40:45]}")
                print(f"  max(|h_L - h_R|): {np.max(np.abs(h_L - h_R)):.3e}")

            # 
            if self.order == 2:
                Q_L, Q_R = self._muscl_reconstruction(Q_ext)
            else:
                Q_L = Q_ext[:-1]
                Q_R = Q_ext[1:]
        else:
            # hQ
            # NumbaHLLHLLC
            if self.use_numba and not self.well_balanced and self.riemann_solver in ['hll', 'hllc', 'exact']:
                # [JIT] Numba acceleration path
                if self.order == 2:
                    h_L, h_R = muscl_reconstruction_numba(h_ext)
                    Q_L, Q_R = muscl_reconstruction_numba(Q_ext)
                else:
                    h_L = h_ext[:-1]
                    h_R = h_ext[1:]
                    Q_L = Q_ext[:-1]
                    Q_R = Q_ext[1:]

                # Numba
                if self.riemann_solver == 'hllc':
                    # HLLCPhase 9.2
                    F_h = np.zeros(len(h_L))
                    F_Q = np.zeros(len(h_L))
                    for i in range(len(h_L)):
                        F_h[i], F_Q[i] = hllc_flux_numba(
                            h_L[i], Q_L[i], h_R[i], Q_R[i],
                            self.B, self.g, self.eps_dry
                        )
                elif self.riemann_solver == 'exact':
                    # Phase 9.3
                    F_h = np.zeros(len(h_L))
                    F_Q = np.zeros(len(h_L))
                    for i in range(len(h_L)):
                        F_h[i], F_Q[i] = exact_riemann_flux_numba(
                            h_L[i], Q_L[i], h_R[i], Q_R[i],
                            self.B, self.g, self.eps_dry,
                            max_iter=50, tol=1e-10
                        )
                else:
                    # HLL
                    F_h, F_Q = compute_all_fluxes_numba(
                        h_L, h_R, Q_L, Q_R, self.B, self.g, self.eps_dry
                    )

                # Enforce boundary fluxes so prescribed Q/h boundaries remain
                # consistent with the finite-volume update.
                self._enforce_boundary_fluxes(F_h, F_Q, h, Q)

                # 
                self.last_F_h = F_h.copy()
                self.last_F_Q = F_Q.copy()

                # +Numba
                dh_dt, dQ_dt = compute_spatial_derivatives_numba(
                    F_h, F_Q, self.S0, h, Q, self.B, self.g, self.n, self.eps_dry, self.dx
                )

                return dh_dt, dQ_dt
            else:
                # Python
                if self.order == 2:
                    h_L, h_R = self._muscl_reconstruction(h_ext)
                    Q_L, Q_R = self._muscl_reconstruction(Q_ext)
                else:
                    h_L = h_ext[:-1]
                    h_R = h_ext[1:]
                    Q_L = Q_ext[:-1]
                    Q_R = Q_ext[1:]

        # Python
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        # DEBUG: Print interface states for Lake at Rest diagnosis
        if DEBUG and self.well_balanced and self.t < 1e-6:  # Only at t=0
            print(f"\n[DEBUG] Interface states at t={self.t:.2e}:")
            print(f"  h_L: {h_L}")
            print(f"  h_R: {h_R}")
            print(f"  Q_L: {Q_L}")
            print(f"  Q_R: {Q_R}")

        for i in range(n + 1):
            # ii-1i
            # h_L, h_Rhydrostatic reconstruction
            if self.riemann_solver == 'hllc':
                F_h[i], F_Q[i] = self._hllc_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i]
                )
            elif self.riemann_solver == 'exact':
                F_h[i], F_Q[i] = self._exact_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i]
                )
            else:  # hll
                F_h[i], F_Q[i] = self._hll_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i]
                )

        # Enforce boundary fluxes so prescribed Q/h boundaries remain
        # consistent with the finite-volume update.
        self._enforce_boundary_fluxes(F_h, F_Q, h, Q)

        # 
        self.last_F_h = F_h.copy()
        self.last_F_Q = F_Q.copy()

        # DEBUG: Print computed fluxes
        if DEBUG and self.well_balanced and self.t < 1e-6:
            print(f"[DEBUG] Computed fluxes:")
            print(f"  F_h: {F_h}")
            print(f"  F_Q: {F_Q}")

        # z_b
        z_b_interface_for_source = None
        if self.source_term_method == 'interface' and not self.well_balanced:
            z_b_ext = np.zeros(n + 2)
            z_b_ext[1:n+1] = self.z_b
            # ghost: 
            z_b_ext[0] = self.z_b[0] - (self.z_b[1] - self.z_b[0]) if n > 1 else self.z_b[0]
            # ghost: 
            z_b_ext[n+1] = self.z_b[n-1] + (self.z_b[n-1] - self.z_b[n-2]) if n > 1 else self.z_b[n-1]
            # 
            z_b_interface_for_source = 0.5 * (z_b_ext[:-1] + z_b_ext[1:])

        # Python
        for i in range(n):
            # i
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx

            if self.well_balanced:
                # Hydrostatic reconstruction needs a matching geometric
                # correction so lake-at-rest states remain stationary.
                h_star_left = 0.5 * (h_L[i] + h_R[i])
                h_star_right = 0.5 * (h_L[i+1] + h_R[i+1])
                dz_interface = z_b_interface[i+1] - z_b_interface[i]
                h_star_avg = 0.5 * (h_star_left + h_star_right)
                dQ_dt[i] += -self.g * h_star_avg * self.B * dz_interface / self.dx

            # Well-balanced: reconstruction
            #
            # AudusseHydrostatic Reconstruction
            #  h* = max(0, eta - z_interface) 
            # 
            #
            # 706-724S_geo

            # Zhou's Surface Gradient Method
            # source_term_method='interface'
            if self.source_term_method == 'interface' and not self.well_balanced:
                # Zhou
                # S_bed = -g * h * B * ∂z_b/∂x
                # : S_bed = -g * h * B * (z_b[i+1/2] - z_b[i-1/2]) / dx
                dz = z_b_interface_for_source[i+1] - z_b_interface_for_source[i]
                h_for_source = h[i]  # 
                S_bed_interface = -self.g * h_for_source * self.B * dz / self.dx

                # 
                S_friction = self._compute_friction_source_term(h[i], Q[i], i)

                # 
                dQ_dt[i] += S_bed_interface + S_friction

            # 
            elif self.source_term_method == 'standard' and not self.well_balanced:
                dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

            # Well-balanced
            elif self.well_balanced:
                dQ_dt[i] += self._compute_source_term(h[i], Q[i], i)

        return dh_dt, dQ_dt

    def _compute_flux_only_rhs(self, h: np.ndarray, Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        Strang Splitting

        dU/dt = -1/dx*(F_{i+1/2} - F_{i-1/2})

        Returns:
            dh/dt, dQ/dt ()
        """
        n = len(h)

        # 
        dh_dt = np.zeros(n)
        dQ_dt = np.zeros(n)

        # ghost cells
        h_ext, Q_ext = self._extend_with_ghosts(h, Q)

        # Well-balanced
        if self.well_balanced:
            # 
            eta = h + self.z_b
            eta_ext = np.zeros(n + 2)
            eta_ext[1:n+1] = eta

            # ghost
            if self.bc_left['type'] == 'h':
                value = self.bc_left['value']
                h_bc = value if not callable(value) else value(self.t)
                z_b_ghost = (2.0 * self.z_b[0] - self.z_b[1]) if n > 1 else self.z_b[0]
                eta_bc = h_bc + z_b_ghost
                eta_ext[0] = eta_bc
            else:  # Q boundary
                eta_ext[0] = eta[0]

            # ghost
            if self.bc_right['type'] == 'h':
                value = self.bc_right['value']
                h_bc = value if not callable(value) else value(self.t)
                z_b_ghost = (2.0 * self.z_b[n-1] - self.z_b[n-2]) if n > 1 else self.z_b[n-1]
                eta_bc = h_bc + z_b_ghost
                eta_ext[n+1] = eta_bc
            else:  # Q boundary
                eta_ext[n+1] = eta[n-1]

            # η
            if self.order == 2:
                eta_L, eta_R = self._muscl_reconstruction(eta_ext)
            else:
                eta_L = eta_ext[:-1]
                eta_R = eta_ext[1:]

            # 
            z_b_ext = np.zeros(n + 2)
            z_b_ext[1:n+1] = self.z_b
            z_b_ext[0] = self.z_b[0] - (self.z_b[1] - self.z_b[0]) if n > 1 else self.z_b[0]
            z_b_ext[n+1] = self.z_b[n-1] + (self.z_b[n-1] - self.z_b[n-2]) if n > 1 else self.z_b[n-1]
            z_b_interface = np.maximum(z_b_ext[:-1], z_b_ext[1:])

            # ηh
            h_L = np.maximum(0.0, eta_L - z_b_interface)
            h_R = np.maximum(0.0, eta_R - z_b_interface)

            # Q
            if self.order == 2:
                Q_L, Q_R = self._muscl_reconstruction(Q_ext)
            else:
                Q_L = Q_ext[:-1]
                Q_R = Q_ext[1:]
        else:
            # 
            if self.use_numba and (self.riemann_solver == 'hll' or self.riemann_solver == 'hllc'):
                if self.order == 2:
                    h_L, h_R = muscl_reconstruction_numba(h_ext)
                    Q_L, Q_R = muscl_reconstruction_numba(Q_ext)
                else:
                    h_L = h_ext[:-1]
                    h_R = h_ext[1:]
                    Q_L = Q_ext[:-1]
                    Q_R = Q_ext[1:]

                # 
                if self.riemann_solver == 'hllc':
                    # HLLCPhase 9.2
                    F_h = np.zeros(len(h_L))
                    F_Q = np.zeros(len(h_L))
                    for i in range(len(h_L)):
                        F_h[i], F_Q[i] = hllc_flux_numba(
                            h_L[i], Q_L[i], h_R[i], Q_R[i],
                            self.B, self.g, self.eps_dry
                        )
                else:
                    # HLL
                    F_h, F_Q = compute_all_fluxes_numba(
                        h_L, h_R, Q_L, Q_R, self.B, self.g, self.eps_dry
                    )

                # 
                for i in range(n):
                    dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
                    dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx

                    # Well-balanced
                    if self.well_balanced:
                        h_star_left = 0.5 * (h_L[i] + h_R[i])
                        h_star_right = 0.5 * (h_L[i+1] + h_R[i+1])
                        dz_interface = z_b_interface[i+1] - z_b_interface[i]
                        h_star_avg = 0.5 * (h_star_left + h_star_right)
                        S_geo = -self.g * h_star_avg * self.B * dz_interface / self.dx
                        dQ_dt[i] += S_geo

                return dh_dt, dQ_dt
            else:
                if self.order == 2:
                    h_L, h_R = self._muscl_reconstruction(h_ext)
                    Q_L, Q_R = self._muscl_reconstruction(Q_ext)
                else:
                    h_L = h_ext[:-1]
                    h_R = h_ext[1:]
                    Q_L = Q_ext[:-1]
                    Q_R = Q_ext[1:]

        # Python
        F_h = np.zeros(n + 1)
        F_Q = np.zeros(n + 1)

        for i in range(n + 1):
            if self.riemann_solver == 'hllc':
                F_h[i], F_Q[i] = self._hllc_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i]
                )
            else:  # hll
                F_h[i], F_Q[i] = self._hll_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i]
                )

        # 
        self.last_F_h = F_h.copy()
        self.last_F_Q = F_Q.copy()

        # 
        for i in range(n):
            dh_dt[i] = -(F_h[i+1] - F_h[i]) / self.dx
            dQ_dt[i] = -(F_Q[i+1] - F_Q[i]) / self.dx

            # Well-balanced
            if self.well_balanced:
                h_star_left = 0.5 * (h_L[i] + h_R[i])
                h_star_right = 0.5 * (h_L[i+1] + h_R[i+1])
                dz_interface = z_b_interface[i+1] - z_b_interface[i]
                h_star_avg = 0.5 * (h_star_left + h_star_right)
                S_geo = -self.g * h_star_avg * self.B * dz_interface / self.dx
                dQ_dt[i] += S_geo

        return dh_dt, dQ_dt

    def _solve_source_ode(self, h: np.ndarray, Q: np.ndarray, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        ODE

        Strang Splitting

        dh/dt = 0  ()
        dQ/dt = S_Q = g*A*(S0 - Sf)

        

        Args:
            h: 
            Q: 
            dt: 

        Returns:
            h_new, Q_new ()
        """
        n = len(h)

        # h
        h_new = h.copy()
        Q_new = Q.copy()

        # QODE
        for i in range(n):
            # 
            S_Q = self._compute_source_term(h[i], Q[i], i)

            # 
            Q_new[i] = Q[i] + dt * S_Q

        return h_new, Q_new

    def _muscl_reconstruction(self, phi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        MUSCL+TVD
        
        phi_iphi_{i-1/2}^R  phi_{i+1/2}^L
        
        Args:
            phi:  [n+2] (ghost cells)
        
        Returns:
            phi_L:  [n+1]
            phi_R:  [n+1]
        """
        n = len(phi) - 2  # 
        
        phi_L = np.zeros(n + 1)
        phi_R = np.zeros(n + 1)
        
        # Minmod
        def minmod(a, b):
            if a * b <= 0:
                return 0.0
            elif abs(a) < abs(b):
                return a
            else:
                return b
        
        for i in range(n + 1):
            # ii-1i
            # : i-1+1 = i ()
            # : i+1 ()
            
            # i
            if i > 0:
                slope_L = minmod(
                    phi[i+1] - phi[i],
                    phi[i] - phi[i-1]
                )
                phi_L[i] = phi[i] + 0.5 * slope_L
            else:
                phi_L[i] = phi[i]
            
            # i+1
            if i < n:
                slope_R = minmod(
                    phi[i+2] - phi[i+1],
                    phi[i+1] - phi[i]
                )
                phi_R[i] = phi[i+1] - 0.5 * slope_R
            else:
                phi_R[i] = phi[i+1]
        
        return phi_L, phi_R

    def _hydrostatic_reconstruction(
        self,
        h_L: float,
        h_R: float,
        z_b_L: float,
        z_b_R: float
    ) -> Tuple[float, float]:
        """
        Hydrostatic Reconstruction (Audusse et al. 2004)

        η=h+z_bh
        (Q=0, ∂η/∂x=0)0

        
        1.  z*= max(z_b_L, z_b_R)
        2. h*_L = max(0, η_L - z*), h*_R = max(0, η_R - z*)
        3. h*

        Args:
            h_L: 
            h_R: 
            z_b_L: 
            z_b_R: 

        Returns:
            h*_L, h*_R: 
        """
        # 
        eta_L = h_L + z_b_L
        eta_R = h_R + z_b_R

        # max
        z_interface = max(z_b_L, z_b_R)

        # 
        h_star_L = max(0.0, eta_L - z_interface)
        h_star_R = max(0.0, eta_R - z_interface)

        return h_star_L, h_star_R

    def _hllc_flux(
        self,
        h_L: float,
        Q_L: float,
        h_R: float,
        Q_R: float
    ) -> Tuple[float, float]:
        """
        HLLC Riemann- Phase 9.2

        HLLC = HLL with Contact wave
        HLL
        Lake at Rest

        :
        - NaN
        - 
        - Toro (2009)

        : Toro (2009) "Riemann Solvers", Chapter 10.3
        """
        # NumbaHLLC
        return hllc_flux_numba(h_L, Q_L, h_R, Q_R, self.B, self.g, self.eps_dry)

    def _exact_flux(
        self,
        h_L: float,
        Q_L: float,
        h_R: float,
        Q_R: float
    ) -> Tuple[float, float]:
        """
        Riemann- Phase 9.3

        Riemann

        :
        - 
        - 
        - 
        - Lake at Rest

        :
        - HLL2-3Newton
        - HLLC2
        - 

        : Toro (2009) "Riemann Solvers", Chapter 13
        """
        # Riemann
        return exact_riemann_flux(
            h_L, Q_L, h_R, Q_R,
            self.B, self.g, self.eps_dry,
            max_iter=50, tol=1e-10
        )

    def _hll_flux(
        self,
        h_L: float,
        Q_L: float,
        h_R: float,
        Q_R: float
    ) -> Tuple[float, float]:
        """
        HLL Riemann

        
        1. 
        2. 
        3. 

        Phase 6.5: Numba JIT2-5x
        """
        # Numba JIT- Phase 6.5
        if self.use_numba and NUMBA_KERNELS_AVAILABLE:
            return hll_flux_kernel(
                h_L, Q_L, h_R, Q_R,
                self.B, self.g, self.eps_dry,
                self.entropy_fix, self.critical_flow_treatment
            )

        # Python
        # 
        if h_L < self.eps_dry and h_R < self.eps_dry:
            return 0.0, 0.0

        # 
        A_L = max(h_L * self.B, self.eps_dry * self.B)
        u_L = Q_L / A_L
        c_L = np.sqrt(self.g * max(h_L, 0.0))

        # 
        A_R = max(h_R * self.B, self.eps_dry * self.B)
        u_R = Q_R / A_R
        c_R = np.sqrt(self.g * max(h_R, 0.0))

        # Davis
        S_L = min(u_L - c_L, u_R - c_R)
        S_R = max(u_L + c_L, u_R + c_R)

        # Entropy
        if self.entropy_fix:
            # delta10%
            delta = 0.1 * max(abs(S_L), abs(S_R), 1e-10)

            # entropy
            S_L = self._entropy_fix(S_L, delta)
            S_R = self._entropy_fix(S_R, delta)

        # 
        F_h_L = Q_L
        F_Q_L = Q_L**2 / A_L + 0.5 * self.g * h_L**2 * self.B

        F_h_R = Q_R
        F_Q_R = Q_R**2 / A_R + 0.5 * self.g * h_R**2 * self.B

        # HLL
        if S_L >= 0:
            # 
            F_h = F_h_L
            F_Q = F_Q_L
        elif S_R <= 0:
            # 
            F_h = F_h_R
            F_Q = F_Q_R
        else:
            # HLL
            U_h_L = h_L
            U_h_R = h_R
            U_Q_L = Q_L
            U_Q_R = Q_R

            dS = S_R - S_L
            if abs(dS) < 1e-12:
                F_h = 0.5 * (F_h_L + F_h_R)
                F_Q = 0.5 * (F_Q_L + F_Q_R)
            else:
                F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / dS
                F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / dS

        # 
        if self.critical_flow_treatment:
            # Froude
            Fr_L = abs(u_L) / c_L if c_L > 1e-10 else 0.0
            Fr_R = abs(u_R) / c_R if c_R > 1e-10 else 0.0

            # Froude
            Fr_avg = 0.5 * (Fr_L + Fr_R)

            # 0.9 < Fr < 1.1
            if 0.9 < Fr_avg < 1.1:
                # Fr=1
                # alphaFr=10.5Fr=0.91.10
                alpha = 0.5 * (1.0 - abs(Fr_avg - 1.0) / 0.1)

                # Lax-Friedrichs
                max_speed = max(abs(u_L) + c_L, abs(u_R) + c_R, 1e-10)

                # 
                dissipation_h = alpha * max_speed * (h_R - h_L)
                dissipation_Q = alpha * max_speed * (Q_R - Q_L)

                F_h -= dissipation_h
                F_Q -= dissipation_Q

        return F_h, F_Q
    
    def _compute_friction_source_term(self, h: float, Q: float, cell_idx: int) -> float:
        """
        interface

        Args:
            h:  (m)
            Q:  (m³/s)
            cell_idx: 

        Returns:
            
        """
        # 
        h_safe = max(h, self.eps_dry)
        geom = self.cross_section.compute_geometry(h_safe)
        A = geom.area
        R = geom.hydraulic_radius

        #
        if R > 1e-10 and abs(Q) > 1e-6:
            Sf = self.n**2 * Q**2 / (A**2 * R**(4.0/3.0))
            Sf = min(Sf, 100.0)  # Cap friction slope to prevent overflow
            Sf = np.sign(Q) * Sf
        else:
            Sf = 0.0

        #
        return -self.g * A * Sf

    def _compute_source_term(self, h: float, Q: float, cell_idx: int) -> float:
        """
        +

        S_Q = g*A*(S0 - Sf)
        Well-balancedS_Q = -g*A*Sf 

        Args:
            h:  (m)
            Q:  (m³/s)
            cell_idx: 

        Returns:
            

        Phase 6.5: Numba JIT2-5x
        """
        # 
        h_safe = max(h, self.eps_dry)
        geom = self.cross_section.compute_geometry(h_safe)
        A = geom.area
        R = geom.hydraulic_radius

        # Numba JIT- Phase 6.5
        if self.use_numba and NUMBA_KERNELS_AVAILABLE:
            return compute_source_term_kernel(
                h, Q, A, R, self.n, self.g,
                self.S0[cell_idx], self.well_balanced
            )

        # Python
        #
        if R > 1e-10 and abs(Q) > 1e-6:
            Sf = self.n**2 * Q**2 / (A**2 * R**(4.0/3.0))
            Sf = min(Sf, 100.0)  # Cap friction slope to prevent overflow
            Sf = np.sign(Q) * Sf
        else:
            Sf = 0.0

        # Well-balancedhydrostatic reconstruction
        # 
        if self.well_balanced:
            return -self.g * A * Sf
        else:
            # 
            return self.g * A * (self.S0[cell_idx] - Sf)
    
    def _extend_with_ghosts(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """ghost cells"""
        n = len(h)
        h_ext = np.zeros(n + 2)
        Q_ext = np.zeros(n + 2)

        # 
        h_ext[1:n+1] = h
        Q_ext[1:n+1] = Q

        # ghost
        if self.bc_left['type'] == 'wall':
            # Reflective (wall/no-penetration) boundary
            # hQ
            h_ext[0] = h[0]
            Q_ext[0] = -Q[0]  # Reflective
        elif self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            h_ext[0] = value if not callable(value) else value(self.t)
            Q_ext[0] = Q[0]  # 
        elif self.bc_left['type'] == 'Q':
            h_ext[0] = h[0]
            value = self.bc_left['value']
            Q_ext[0] = value if not callable(value) else value(self.t)
        elif self.bc_left['type'] == 'critical':
            # h_cQ
            if self.bc_right['type'] == 'Q':
                # Q
                Q_boundary = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            else:
                # 
                Q_boundary = np.mean(Q[:min(10, n)])
            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_boundary, B=self.B)
            # hQ
            h_ext[0] = h_c
            Q_ext[0] = Q[0]  # 
        elif self.bc_left['type'] == 'supercritical':
            # hQ
            h_bc_value = self.bc_left['h']
            Q_bc_value = self.bc_left['Q']
            h_bc, u_bc = self.characteristic_bc.apply_supercritical_inlet(
                h_bc_value=h_bc_value, Q_bc_value=Q_bc_value, B=self.B
            )
            h_ext[0] = h_bc
            Q_ext[0] = Q_bc_value

        # ghost
        if self.bc_right['type'] == 'wall':
            # Reflective (wall/no-penetration) boundary
            # hQ
            h_ext[n+1] = h[n-1]
            Q_ext[n+1] = -Q[n-1]  # Reflective
        elif self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            h_ext[n+1] = value if not callable(value) else value(self.t)
            Q_ext[n+1] = Q[n-1]  # 
        elif self.bc_right['type'] == 'Q':
            h_ext[n+1] = h[n-1]
            value = self.bc_right['value']
            Q_ext[n+1] = value if not callable(value) else value(self.t)
        elif self.bc_right['type'] == 'critical':
            # h_cQ
            if self.bc_left['type'] == 'Q':
                # Q
                Q_boundary = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            else:
                # 
                Q_boundary = np.mean(Q[-min(10, n):])
            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_boundary, B=self.B)
            # hQover-constrain
            h_ext[n+1] = h_c
            Q_ext[n+1] = Q[n-1]  # 
        elif self.bc_right['type'] == 'supercritical':
            # 
            h_bc, u_bc = self.characteristic_bc.apply_supercritical_outlet(
                h_interior=h[n-1], u_interior=Q[n-1]/(h[n-1]*self.B) if h[n-1] > self.eps_dry else 0.0
            )
            h_ext[n+1] = h_bc
            Q_ext[n+1] = u_bc * h_bc * self.B

        return h_ext, Q_ext
    
    def _apply_bc(
        self,
        h: np.ndarray,
        Q: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        

        ****
        relaxation

        
        - supercritical: 
        - h/Q: relaxation_factor=0.2
        - critical: 

        
        1. 20%
        2. 
        3. 
        """
        # 
        #
        # Dirichlet'h''Q'
        # - 
        # - ghost cells
        # - ~0.2%
        # - ~1-5%
        #
        # supercritical
        # - 
        # - 

        # supercritical
        if self.bc_left['type'] == 'supercritical':
            h_bc_value = self.bc_left['h']
            Q_bc_value = self.bc_left['Q']
            h_bc, u_bc = self.characteristic_bc.apply_supercritical_inlet(
                h_bc_value=h_bc_value, Q_bc_value=Q_bc_value, B=self.B
            )
            h[0] = h_bc
            Q[0] = Q_bc_value

        if self.bc_right['type'] == 'supercritical':
            h_bc, u_bc = self.characteristic_bc.apply_supercritical_outlet(
                h_interior=h[-2] if len(h) > 1 else h[-1],
                u_interior=Q[-2]/(h[-2]*self.B) if len(h) > 1 and h[-2] > self.eps_dry else 0.0
            )
            h[-1] = h_bc
            Q[-1] = u_bc * h_bc * self.B

        # 'h', 'Q', 'critical'
        # relaxation
        # Slightly under-relax mixed h/Q Dirichlet boundaries to reduce
        # steady-state outlet drift in long subcritical runs.
        relaxation_factor = 0.48

        # relaxation
        if self.bc_left['type'] == 'h':
            value = self.bc_left['value']
            h_target = value if not callable(value) else value(self.t)
            h[0] = h[0] + relaxation_factor * (h_target - h[0])
        elif self.bc_left['type'] == 'Q':
            value = self.bc_left['value']
            Q_target = value if not callable(value) else value(self.t)
            Q[0] = Q[0] + relaxation_factor * (Q_target - Q[0])
        elif self.bc_left['type'] == 'critical':
            if self.bc_right['type'] == 'Q':
                Q_boundary = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            else:
                Q_boundary = np.mean(Q[:min(10, len(Q))])
            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_boundary, B=self.B)
            h[0] = h[0] + relaxation_factor * (h_c - h[0])

        # relaxation
        if self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            h_target = value if not callable(value) else value(self.t)
            h[-1] = h[-1] + relaxation_factor * (h_target - h[-1])
        elif self.bc_right['type'] == 'Q':
            value = self.bc_right['value']
            Q_target = value if not callable(value) else value(self.t)
            Q[-1] = Q[-1] + relaxation_factor * (Q_target - Q[-1])
        elif self.bc_right['type'] == 'critical':
            if self.bc_left['type'] == 'Q':
                Q_boundary = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            else:
                Q_boundary = np.mean(Q[-min(10, len(Q)):])
            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_boundary, B=self.B)
            h[-1] = h[-1] + relaxation_factor * (h_c - h[-1])

        return h, Q

    def _enforce_boundary_fluxes(
        self,
        F_h: np.ndarray,
        F_Q: np.ndarray,
        h: np.ndarray,
        Q: np.ndarray
    ):
        """
        

        Riemann
        

        Args:
            F_h:  [n+1]
            F_Q:  [n+1]
            h:  [n]
            Q:  [n]
        """
        n = len(h)

        # 0ghost cell0
        if self.bc_left['type'] == 'Q':
            # Q
            Q_bc = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            h_bc = h[0]  # 

            #
            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                c_bc = np.sqrt(self.g * h_bc) if h_bc > self.eps_dry else 0.0
                u_max = 10.0 * max(c_bc, 1.0)  # Physical velocity limit
                u_bc = np.clip(u_bc, -u_max, u_max)
                F_h[0] = Q_bc
                F_Q[0] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[0] = 0.0
                F_Q[0] = 0.0

        elif self.bc_left['type'] == 'h':
            # hRiemann
            # hQ
            #
            pass

        elif self.bc_left['type'] == 'supercritical':
            # hQ
            h_bc = self.bc_left['h']
            Q_bc = self.bc_left['Q']

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                c_bc = np.sqrt(self.g * h_bc) if h_bc > self.eps_dry else 0.0
                u_max = 10.0 * max(c_bc, 1.0)  # Physical velocity limit
                u_bc = np.clip(u_bc, -u_max, u_max)
                F_h[0] = Q_bc
                F_Q[0] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[0] = 0.0
                F_Q[0] = 0.0

        elif self.bc_left['type'] == 'critical':
            # 
            if self.bc_right['type'] == 'Q':
                Q_bc = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            else:
                Q_bc = Q[0]

            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_bc, B=self.B)

            if h_c > self.eps_dry:
                F_h[0] = Q_bc
                F_Q[0] = Q_bc * u_c + 0.5 * self.g * h_c * h_c * self.B
            else:
                F_h[0] = 0.0
                F_Q[0] = 0.0

        # nn-1ghost cell
        if self.bc_right['type'] == 'Q':
            # Q
            Q_bc = self.bc_right['value'] if not callable(self.bc_right['value']) else self.bc_right['value'](self.t)
            h_bc = h[n-1]

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                c_bc = np.sqrt(self.g * h_bc) if h_bc > self.eps_dry else 0.0
                u_max = 10.0 * max(c_bc, 1.0)  # Physical velocity limit
                u_bc = np.clip(u_bc, -u_max, u_max)
                F_h[n] = Q_bc
                F_Q[n] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[n] = 0.0
                F_Q[n] = 0.0

        elif self.bc_right['type'] == 'h':
            value = self.bc_right['value']
            h_bc = value if not callable(value) else value(self.t)
            Q_bc = Q[n-1]

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                c_bc = np.sqrt(self.g * h_bc)
                u_max = 10.0 * max(c_bc, 1.0)
                u_bc = np.clip(u_bc, -u_max, u_max)
                F_h[n] = Q_bc
                F_Q[n] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[n] = 0.0
                F_Q[n] = 0.0

        elif self.bc_right['type'] == 'supercritical':
            #
            h_bc = h[n-1]
            Q_bc = Q[n-1]

            if h_bc > self.eps_dry:
                u_bc = Q_bc / (self.B * h_bc)
                c_bc = np.sqrt(self.g * h_bc) if h_bc > self.eps_dry else 0.0
                u_max = 10.0 * max(c_bc, 1.0)  # Physical velocity limit
                u_bc = np.clip(u_bc, -u_max, u_max)
                F_h[n] = Q_bc
                F_Q[n] = Q_bc * u_bc + 0.5 * self.g * h_bc * h_bc * self.B
            else:
                F_h[n] = 0.0
                F_Q[n] = 0.0

        elif self.bc_right['type'] == 'critical':
            # 
            if self.bc_left['type'] == 'Q':
                Q_bc = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            else:
                Q_bc = Q[n-1]

            h_c, u_c = self.characteristic_bc.apply_critical_depth_bc(Q=Q_bc, B=self.B)

            if h_c > self.eps_dry:
                F_h[n] = Q_bc
                F_Q[n] = Q_bc * u_c + 0.5 * self.g * h_c * h_c * self.B
            else:
                F_h[n] = 0.0
                F_Q[n] = 0.0

    def _compute_total_mass(self, exclude_boundary_cells=False) -> float:
        """
        

        Args:
            exclude_boundary_cells: 
                - True: 
                - False: 
        """
        if exclude_boundary_cells:
            # 
            exclude_left = self.bc_left['type'] in ['supercritical', 'h', 'Q', 'critical']
            exclude_right = self.bc_right['type'] in ['supercritical', 'h', 'Q', 'critical']

            # 
            start_idx = 1 if exclude_left else 0
            end_idx = len(self.h) - 1 if exclude_right else len(self.h)

            #  - 
            mass = 0.0
            for i in range(start_idx, end_idx):
                geom = self.cross_section.compute_geometry(max(self.h[i], 0.0))
                mass += geom.area * self.dx
            return mass
        else:
            #  - 
            mass = 0.0
            for i in range(len(self.h)):
                geom = self.cross_section.compute_geometry(max(self.h[i], 0.0))
                mass += geom.area * self.dx
            return mass
    
    def get_mass_conservation_error(self, exclude_boundary_cells=False) -> float:
        """
         (%)

        Args:
            exclude_boundary_cells: False
                - True: 
                - False: 
        """
        current_mass = self._compute_total_mass(exclude_boundary_cells=exclude_boundary_cells)
        if self.initial_mass > 1e-10:
            return (current_mass - self.initial_mass) / self.initial_mass * 100.0
        return 0.0
    
    def get_state(self) -> Dict:
        """"""
        return {
            'x': self.x.copy(),
            'h': self.h.copy(),
            'Q': self.Q.copy(),
            't': self.t,
            'dt': self.dt,
            'step': self.step_count,
            'mass_error': self.get_mass_conservation_error()
        }

    def _entropy_fix(self, lambda_val: float, delta: float) -> float:
        """
        Harten-Hyman Entropy

        

        Args:
            lambda_val: 
            delta: 10%

        Returns:
            
        """
        if abs(lambda_val) >= delta:
            return lambda_val
        else:
            return (lambda_val**2 + delta**2) / (2.0 * delta)

    def compute_froude_number(self, h=None, Q=None) -> np.ndarray:
        """
        Froude

        Fr = u / sqrt(g*h_d)
         h_d =  = A/B (/)

        Args:
            h: self.h
            Q: self.Q

        Returns:
            Froude
        """
        if h is None:
            h = self.h
        if Q is None:
            Q = self.Q

        Fr = np.zeros_like(h)
        for i in range(len(h)):
            if h[i] > self.eps_dry:
                # 
                geom = self.cross_section.compute_geometry(h[i])
                if geom.area > self.eps_dry:
                    u = Q[i] / geom.area
                    # Froude
                    c = np.sqrt(self.g * geom.hydraulic_depth)
                    Fr[i] = u / c if c > 1e-10 else 0.0
                else:
                    Fr[i] = 0.0
            else:
                Fr[i] = 0.0
        return Fr

    def is_critical_flow(self, Fr=None, threshold=0.1) -> np.ndarray:
        """
        

         |Fr - 1.0| < threshold

        Args:
            Fr: Froude
            threshold: 0.1

        Returns:
            True
        """
        if Fr is None:
            Fr = self.compute_froude_number()
        return np.abs(Fr - 1.0) < threshold

    def get_flow_regime(self, Fr=None) -> np.ndarray:
        """
        

        Args:
            Fr: Froude

        Returns:
            0=, 1=, 2=
        """
        if Fr is None:
            Fr = self.compute_froude_number()

        regime = np.zeros_like(Fr, dtype=int)
        regime[Fr < 0.9] = 0  # 
        regime[(Fr >= 0.9) & (Fr <= 1.1)] = 1  # 
        regime[Fr > 1.1] = 2  # 
        return regime


if __name__ == "__main__":
    print("="*80)
    print("Godunov-FVM - ")
    print("="*80)
    
    # 
    print("\n1: ")
    print("-"*80)
    
    solver = GodunvFVMSolver(
        width=10.0,
        length=1000.0,
        n_cells=50,
        manning_n=0.025,
        slope=0.001,
        cfl=0.5,
        order=2
    )
    
    h_init = np.ones(50) * 2.0
    Q_init = np.zeros(50)
    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 2.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 100
    for _ in range(100):
        solver.step()
    
    state = solver.get_state()
    print(f"\n (100):")
    print(f"  : {state['mass_error']:.6f}%")
    print(f"  max|h-2.0|: {np.max(np.abs(state['h'] - 2.0)):.6e} m")
    print(f"  max|Q|: {np.max(np.abs(state['Q'])):.6e} m³/s")
    print(f"  <0.5%: {'' if abs(state['mass_error']) < 0.5 else ''}")
    
    print("\n" + "="*80)
