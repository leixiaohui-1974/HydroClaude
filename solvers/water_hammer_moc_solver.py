#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MOC / Water Hammer MOC Solver

(Method of Characteristics)

 / Governing Equations:
- : ∂H/∂t + (a²/gA) * ∂Q/∂x = 0
- :   ∂Q/∂t + gA * ∂H/∂x + (f*Q*|Q|)/(2*D*A) = 0

 / Characteristic Lines:
- C⁺: dx/dt = +a
- C⁻: dx/dt = -a

 / Compatibility Equations:
- C⁺: H_P + B*Q_P = H_A + B*Q_A - R*Q_A*|Q_A|
- C⁻: H_P - B*Q_P = H_B - B*Q_B + R*Q_B*|Q_B|

 / Where:
- B = a / (g*A)
- R = f*Δt / (2*D*A)

: HydroClaude Team
: 2025-10-30
"""

import numpy as np
from typing import Dict, Optional, Callable, Tuple
from dataclasses import dataclass


@dataclass
class WaterHammerBoundary:
    """
     / Water Hammer Boundary Condition

     / Boundary Types:
    - 'reservoir':  / Constant head reservoir
    - 'valve':  / Valve
    - 'dead_end':  / Dead end
    """

    bc_type: str
    value: Optional[float] = None  # For reservoir: H_reservoir; For valve: opening_ratio
    closure_function: Optional[Callable[[float], float]] = None  # τ(t), 


class WaterHammerMOCSolver:
    """
    (MOC)

    Method of Characteristics solver for water hammer analysis in pipelines.

    Attributes:
        L (float):  / Pipe length (m)
        D (float):  / Pipe diameter (m)
        A (float):  / Pipe area (m²)
        f (float):  / Friction factor
        a (float):  / Wave speed (m/s)
        dx (float):  / Spatial step (m)
        dt (float):  / Time step (s)
        nx (int):  / Number of spatial nodes
        g (float):  / Gravitational acceleration (m/s²)

    Examples:
        >>> solver = WaterHammerMOCSolver(L=1000, D=0.5, f=0.02, wave_speed=1000)
        >>> solver.set_grid(nx=51)
        >>> bc_up = WaterHammerBoundary('reservoir', value=100.0)
        >>> bc_down = WaterHammerBoundary('valve', closure_function=lambda t: max(0, 1-t/2))
        >>> result = solver.solve_transient(Q0=0.5, H0_up=100, bc_upstream=bc_up,
        ...                                  bc_downstream=bc_down, duration=10.0)
    """

    def __init__(
        self,
        L: float,
        D: float,
        f: float,
        wave_speed: Optional[float] = None,
        K: float = 2.1e9,
        E: float = 2.0e11,
        e: float = 0.01,
        g: float = 9.81
    ):
        """
        

        Initialize water hammer solver

        Args:
            L:  / Pipe length (m)
            D:  / Pipe diameter (m)
            f: Darcy-Weisbach / Friction factor
            wave_speed:  / Wave speed (m/s). K,E,e
            K:  / Bulk modulus of fluid (Pa), 2.1×10⁹ ()
            E:  / Young's modulus of pipe (Pa), 2.0×10¹¹ ()
            e:  / Wall thickness (m)
            g:  / Gravitational acceleration (m/s²)
        """
        self.L = L
        self.D = D
        self.A = np.pi * D**2 / 4.0
        self.f = f
        self.g = g

        #  / Calculate wave speed
        if wave_speed is not None:
            self.a = wave_speed
        else:
            self.a = self.calculate_wave_speed(K, E, e)

        # / Grid parameters (to be set)
        self.dx: Optional[float] = None
        self.dt: Optional[float] = None
        self.nx: Optional[int] = None
        self.z_elevation: Optional[np.ndarray] = None  # Pipe elevation profile

        # MOC / MOC coefficients
        self.B: Optional[float] = None  # B = a / (g*A)
        self.R: Optional[float] = None  # R = f*dt / (2*D*A)

    def calculate_wave_speed(
        self,
        K: float = 2.1e9,
        E: float = 2.0e11,
        e: float = 0.01,
        rho: float = 1000.0
    ) -> float:
        """
         (Korteweg)

        Calculate wave speed using Korteweg formula

        a = √(K/ρ) / √(1 + (K*D)/(E*e))

        Args:
            K:  / Bulk modulus (Pa), 2.1×10⁹ ()
            E:  / Young's modulus (Pa), 2.0×10¹¹ ()
            e:  / Wall thickness (m)
            rho:  / Fluid density (kg/m³)

        Returns:
             / Wave speed (m/s)
        """
        c_fluid = np.sqrt(K / rho)  # 
        correction = 1.0 + (K * self.D) / (E * e)  # 
        a = c_fluid / np.sqrt(correction)
        return a

    def set_grid(self, nx: int, cfl: float = 1.0):
        """
        

        Set computational grid

        Args:
            nx:  / Number of spatial nodes
            cfl: CFL / CFL number (1.0)

        Raises:
            ValueError: CFL
        """
        self.nx = nx
        self.dx = self.L / (nx - 1)

        # CFL / Determine dt from CFL condition
        # CFL = a * dt / dx <= 1
        self.dt = cfl * self.dx / self.a

        # MOC / Calculate MOC coefficients
        self.B = self.a / (self.g * self.A)
        self.R = self.f * self.dt / (2.0 * self.D * self.A)

        # CFL / Verify CFL
        actual_cfl = self.a * self.dt / self.dx
        if actual_cfl > 1.01:  # 1%
            raise ValueError(
                f"CFL: CFL={actual_cfl:.3f} > 1.0. "
                f"nxcfl"
            )

    def solve_transient(
        self,
        Q0: float,
        H0_up: float,
        bc_upstream: WaterHammerBoundary,
        bc_downstream: WaterHammerBoundary,
        duration: float,
        friction_model: str = 'steady'
    ) -> Dict[str, np.ndarray]:
        """
        

        Solve transient flow using MOC

        Args:
            Q0:  / Initial flow rate (m³/s)
            H0_up:  / Initial head at upstream (m)
            bc_upstream:  / Upstream boundary condition
            bc_downstream:  / Downstream boundary condition
            duration:  / Simulation duration (s)
            friction_model:  / Friction model ('steady' or 'unsteady')

        Returns:
             / Results dictionary:
            {
                't':  (nt,) / Time array,
                'x':  (nx,) / Spatial coordinates,
                'Q':  (nt, nx) / Flow rate field,
                'H':  (nt, nx) / Head field,
                'V':  (nt, nx) / Velocity field,
                'p':  (nt, nx) / Pressure field (Pa)
            }
        """
        if self.nx is None or self.dt is None:
            raise RuntimeError("set_grid()")

        #  / Number of time steps (use arange to match actual dt spacing)
        t_array = np.arange(0, duration + self.dt / 2, self.dt)
        nt = len(t_array)
        x_array = np.linspace(0, self.L, self.nx)

        #  / Initialize field variables
        Q = np.zeros((nt, self.nx))
        H = np.zeros((nt, self.nx))

        #  / Initial conditions
        Q[0, :] = Q0

        # / Initial head distribution
        V0 = Q0 / self.A
        hf_per_length = self.f * V0**2 / (2.0 * self.g * self.D)
        for i in range(self.nx):
            H[0, i] = H0_up - hf_per_length * x_array[i]

        #  / Time marching
        for n in range(nt - 1):
            t = t_array[n]

            # 1. MOC / Interior nodes: MOC compatibility equations
            for i in range(1, self.nx - 1):
                # C+  i-1  / C+ from i-1
                Q_A = Q[n, i - 1]
                H_A = H[n, i - 1]
                CP = H_A + self.B * Q_A - self.R * Q_A * abs(Q_A)

                # C-  i+1  / C- from i+1
                Q_B = Q[n, i + 1]
                H_B = H[n, i + 1]
                CM = H_B - self.B * Q_B + self.R * Q_B * abs(Q_B)

                #  P  / Solve for point P
                # H_P + B*Q_P = CP
                # H_P - B*Q_P = CM
                H[n + 1, i] = 0.5 * (CP + CM)
                Q[n + 1, i] = (CP - CM) / (2.0 * self.B)

            # 2.  / Upstream boundary (i=0)
            H[n + 1, 0], Q[n + 1, 0] = self._apply_upstream_bc(
                bc_upstream, t + self.dt, Q[n, 1], H[n, 1]
            )

            # 3.  / Downstream boundary (i=nx-1)
            H[n + 1, -1], Q[n + 1, -1] = self._apply_downstream_bc(
                bc_downstream, t + self.dt, Q[n, -2], H[n, -2]
            )

        #  / Calculate velocity and pressure
        V = Q / self.A
        # Pressure = rho * g * (H - z_elevation), gauge pressure
        # H is piezometric head = z + p/(rho*g), so p = rho*g*(H - z)
        if self.z_elevation is not None:
            z_elev = self.z_elevation
        else:
            # Default: assume horizontal pipe at z=0
            z_elev = np.zeros(self.nx)
        p = 1000.0 * self.g * (H - z_elev[np.newaxis, :])  # gauge pressure (Pa)

        return {
            't': t_array,
            'x': x_array,
            'Q': Q,
            'H': H,
            'V': V,
            'p': p
        }

    def _apply_upstream_bc(
        self,
        bc: WaterHammerBoundary,
        t: float,
        Q_next: float,
        H_next: float
    ) -> Tuple[float, float]:
        """
        

        Apply upstream boundary condition

        Args:
            bc:  / Boundary condition
            t:  / Current time (s)
            Q_next:  / Flow at adjacent node (m³/s)
            H_next:  / Head at adjacent node (m)

        Returns:
            (H_boundary, Q_boundary):  / Boundary head and flow
        """
        # C-  / C- characteristic from i=1
        CM = H_next - self.B * Q_next + self.R * Q_next * abs(Q_next)

        if bc.bc_type == 'reservoir':
            #  / Constant head
            H_b = bc.value
            Q_b = (H_b - CM) / self.B

        elif bc.bc_type == 'dead_end':
            # Q = 0 / Dead end: Q = 0
            Q_b = 0.0
            H_b = CM

        else:
            raise ValueError(f": {bc.bc_type}")

        return H_b, Q_b

    def _apply_downstream_bc(
        self,
        bc: WaterHammerBoundary,
        t: float,
        Q_prev: float,
        H_prev: float
    ) -> Tuple[float, float]:
        """
        

        Apply downstream boundary condition

        Args:
            bc:  / Boundary condition
            t:  / Current time (s)
            Q_prev:  / Flow at adjacent node (m³/s)
            H_prev:  / Head at adjacent node (m)

        Returns:
            (H_boundary, Q_boundary):  / Boundary head and flow
        """
        # C+  / C+ characteristic from i=nx-2
        CP = H_prev + self.B * Q_prev - self.R * Q_prev * abs(Q_prev)

        if bc.bc_type == 'reservoir':
            #  / Constant head
            H_b = bc.value
            Q_b = (CP - H_b) / self.B

        elif bc.bc_type == 'valve':
            #  / Valve boundary
            if bc.closure_function is not None:
                tau = bc.closure_function(t)  #  / Valve opening ratio
            else:
                tau = bc.value if bc.value is not None else 1.0

            if tau < 1e-6:
                #  / Valve fully closed
                Q_b = 0.0
                H_b = CP
            else:
                # / Valve flow equation (nonlinear)
                # Q = τ * K * √H K 
                #  C+ H + B*Q = CP
                # H + B*τ*K*√H = CP
                #  y = √H y² + B*τ*K*y - CP = 0

                # 
                # K ≈ Q_prev / √H_prev
                K = abs(Q_prev) / max(np.sqrt(abs(H_prev)), 0.1) if H_prev > 0 else 0.1

                #  y² + B*τ*K*y - CP = 0
                a_coeff = 1.0
                b_coeff = self.B * tau * K
                c_coeff = -CP

                discriminant = b_coeff**2 - 4 * a_coeff * c_coeff

                if discriminant >= 0:
                    y = (-b_coeff + np.sqrt(discriminant)) / (2 * a_coeff)
                    H_b = y**2
                    Q_b = tau * K * y
                else:
                    # 
                    Q_b = tau * Q_prev
                    H_b = CP - self.B * Q_b

        elif bc.bc_type == 'dead_end':
            # Q = 0 / Dead end: Q = 0
            Q_b = 0.0
            H_b = CP

        else:
            raise ValueError(f": {bc.bc_type}")

        return H_b, Q_b

    def joukowsky_head_rise(self, V0: float) -> float:
        """
        Joukowsky

        Calculate maximum pressure rise using Joukowsky formula

        ΔH = a * ΔV / g

        Args:
            V0:  / Initial velocity (m/s)

        Returns:
             / Maximum head rise (m)
        """
        delta_H = self.a * V0 / self.g
        return delta_H

    def critical_closure_time(self) -> float:
        """
        

        Calculate critical closure time for direct water hammer

        T_critical = 2L / a

        Returns:
             / Critical closure time (s)
        """
        T_critical = 2.0 * self.L / self.a
        return T_critical

    def max_pressure_estimate(self, V0: float, closure_time: float) -> float:
        """
        

        Estimate maximum pressure rise considering closure time

        Args:
            V0:  / Initial velocity (m/s)
            closure_time:  / Valve closure time (s)

        Returns:
             / Maximum head rise (m)
        """
        delta_H_joukowsky = self.joukowsky_head_rise(V0)
        T_critical = self.critical_closure_time()

        if closure_time < T_critical:
            #  / Direct water hammer
            return delta_H_joukowsky
        else:
            #  / Indirect water hammer
            return delta_H_joukowsky * T_critical / closure_time
