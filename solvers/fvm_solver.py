#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
(FVM)


- Godunov
- MUSCL
- Riemann
- TVD slope

: Claude
: 2025-10-23
"""

import numpy as np
import sys
import os

# Riemannslope
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from riemann_solvers import hll_flux_shallow_water, hllc_flux_shallow_water, rusanov_flux
from slope_limiters import compute_limited_slope


class FVMSolver:
    """
    

    
    - Godunov
    - MUSCL + TVD
    - RiemannHLL/HLLC/Rusanov
    - EulerSSP-RK2
    """

    def __init__(self, x_grid, B, S0, n, g=9.81,
                 reconstruction='muscl', limiter='minmod',
                 riemann='hll', time_integrator='ssp_rk2',
                 gates=None):
        """
        FVM

        Args:
            x_grid:  [m]
            B:  [m]
            S0:  [m/m]
            n: Manning [s/m^(1/3)]
            g:  [m/s²]
            reconstruction: 'godunov' ()  'muscl' ()
            limiter: 'minmod', 'vanleer', 'superbee', 'mc'
            riemann: 'hll', 'hllc', 'rusanov'
            time_integrator: 'euler', 'ssp_rk2'
            gates: (position, opening, Cd)
        """
        self.x = np.array(x_grid)
        self.nx = len(self.x)
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g

        # 
        self.x_cell = 0.5 * (self.x[:-1] + self.x[1:])  # 
        self.dx = np.diff(self.x)  # 

        self.ncells = len(self.x_cell)

        # 
        self.reconstruction = reconstruction.lower()
        self.limiter = limiter.lower()
        self.riemann = riemann.lower()
        self.time_integrator = time_integrator.lower()

        #  U = [A, Q]
        # 
        self.U = np.zeros((self.ncells, 2))

        # 
        valid_recon = ['godunov', 'muscl']
        valid_riemann = ['hll', 'hllc', 'rusanov']
        valid_integrator = ['euler', 'ssp_rk2']

        if self.reconstruction not in valid_recon:
            raise ValueError(f"Invalid reconstruction: {reconstruction}")
        if self.riemann not in valid_riemann:
            raise ValueError(f"Invalid Riemann solver: {riemann}")
        if self.time_integrator not in valid_integrator:
            raise ValueError(f"Invalid time integrator: {time_integrator}")

        # 
        self.gates = gates if gates is not None else []
        self.gate_interfaces = []  # 

        # 
        for gate_pos, gate_opening, gate_Cd in self.gates:
            # self.x[i]self.U[i-1]self.U[i]
            # 
            interface_idx = np.argmin(np.abs(self.x - gate_pos))
            self.gate_interfaces.append({
                'index': interface_idx,
                'position': gate_pos,
                'actual_x': self.x[interface_idx],
                'opening': gate_opening,
                'Cd': gate_Cd
            })

        if len(self.gates) > 0:
            print(f"FVM: {len(self.gates)}")
            for i, gate_info in enumerate(self.gate_interfaces):
                print(f"  {i+1}: x={gate_info['position']}m -> {gate_info['index']} (x={gate_info['actual_x']:.1f}m), "
                      f"={gate_info['opening']}m, Cd={gate_info['Cd']}")

    def initialize(self, h0, Q0):
        """
        

        Args:
            h0:  [m] ()
            Q0:  [m³/s] ()
        """
        # 
        if np.isscalar(h0):
            h0 = np.ones(self.ncells) * h0
        if np.isscalar(Q0):
            Q0 = np.ones(self.ncells) * Q0

        #  U = [A, Q]
        A0 = self.B * h0
        self.U[:, 0] = A0
        self.U[:, 1] = Q0

    def get_primitive_variables(self):
        """
         [h, u]

        Returns:
            h:  [m]
            u:  [m/s]
        """
        A = self.U[:, 0]
        Q = self.U[:, 1]

        h = A / self.B
        u = np.where(A > 1e-10, Q / A, 0.0)

        return h, u

    def reconstruct_interface_values(self):
        """
        

        Returns:
            U_L:  [ncells+1, 2]
            U_R:  [ncells+1, 2]
        """
        U_L = np.zeros((self.ncells + 1, 2))
        U_R = np.zeros((self.ncells + 1, 2))

        if self.reconstruction == 'godunov':
            # Godunov
            for i in range(self.ncells + 1):
                if i == 0:
                    # 
                    U_L[i] = self.U[0]
                    U_R[i] = self.U[0]
                elif i == self.ncells:
                    # 
                    U_L[i] = self.U[-1]
                    U_R[i] = self.U[-1]
                else:
                    # 
                    U_L[i] = self.U[i-1]
                    U_R[i] = self.U[i]

        elif self.reconstruction == 'muscl':
            # MUSCL + 
            sigma = np.zeros((self.ncells, 2))

            # 
            for k in range(2):  # AQ
                for i in range(self.ncells):
                    if i == 0:
                        # 
                        sigma[i, k] = 0.0
                    elif i == self.ncells - 1:
                        # 
                        sigma[i, k] = 0.0
                    else:
                        # TVD
                        sigma[i, k] = compute_limited_slope(
                            self.U[i-1, k], self.U[i, k], self.U[i+1, k],
                            self.dx[i-1], self.dx[i], self.dx[i+1] if i+1 < len(self.dx) else self.dx[i],
                            limiter=self.limiter
                        )

            # 
            for i in range(self.ncells + 1):
                if i == 0:
                    # 
                    U_L[i] = self.U[0] - 0.5 * self.dx[0] * sigma[0]
                    U_R[i] = self.U[0] - 0.5 * self.dx[0] * sigma[0]
                elif i == self.ncells:
                    # 
                    U_L[i] = self.U[-1] + 0.5 * self.dx[-1] * sigma[-1]
                    U_R[i] = self.U[-1] + 0.5 * self.dx[-1] * sigma[-1]
                else:
                    # 
                    U_L[i] = self.U[i-1] + 0.5 * self.dx[i-1] * sigma[i-1]
                    U_R[i] = self.U[i] - 0.5 * self.dx[i] * sigma[i]

        return U_L, U_R

    def compute_interface_flux(self, U_L, U_R):
        """
        Riemann

        Riemann

        Args:
            U_L, U_R: 

        Returns:
            F:  [ncells+1, 2]
        """
        F = np.zeros((self.ncells + 1, 2))

        # 
        gate_indices = set()
        gate_map = {}
        for gate_info in self.gate_interfaces:
            idx = gate_info['index']
            gate_indices.add(idx)
            gate_map[idx] = gate_info

        for i in range(self.ncells + 1):
            if i in gate_indices:
                # 
                gate_info = gate_map[i]
                F[i] = self.compute_gate_flux(U_L[i], U_R[i], gate_info)
            else:
                # Riemann
                if self.riemann == 'hll':
                    F[i] = hll_flux_shallow_water(U_L[i], U_R[i], self.B, self.g)
                elif self.riemann == 'hllc':
                    F[i] = hllc_flux_shallow_water(U_L[i], U_R[i], self.B, self.g)
                elif self.riemann == 'rusanov':
                    F[i] = rusanov_flux(U_L[i], U_R[i], self.B, self.g)

        return F

    def compute_gate_flux(self, U_L, U_R, gate_info):
        """
        

        Q = Cd * a * B * sqrt(2*g*Δh)

        Args:
            U_L:  [A_L, Q_L]
            U_R:  [A_R, Q_R]
            gate_info: 

        Returns:
            F:  [F_mass, F_momentum]
        """
        A_L, Q_L = U_L
        A_R, Q_R = U_R

        # 
        h_L = A_L / self.B if A_L > 1e-10 else 1e-10
        h_R = A_R / self.B if A_R > 1e-10 else 1e-10

        # 
        a = gate_info['opening']  # 
        Cd = gate_info['Cd']  # 

        # 
        if h_L > a:
            # 
            delta_h = h_L - h_R
            if delta_h > 0:
                # 
                Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * delta_h)
            else:
                # 
                Q_gate = 0.0
        else:
            # 
            Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * h_L)

        # 
        # 
        F_mass = Q_gate

        # Q * u + 0.5 * g * A * h
        # 
        A_gate = 0.5 * (A_L + A_R)
        h_gate = 0.5 * (h_L + h_R)
        u_gate = Q_gate / A_gate if A_gate > 1e-10 else 0.0

        F_momentum = Q_gate * u_gate + 0.5 * self.g * A_gate * h_gate

        return np.array([F_mass, F_momentum])

    def compute_source_term(self):
        """
         S = [0, gA(S0 - Sf)]

        Returns:
            S:  [ncells, 2]
        """
        S = np.zeros((self.ncells, 2))

        A = self.U[:, 0]
        Q = self.U[:, 1]

        h = A / self.B

        # Manning
        # Sf = n²Q²/(A²R^(4/3))
        # : R = A/P = Bh/(B+2h) ≈ h ()
        R = np.where(h > 1e-10, self.B * h / (self.B + 2 * h), 1e-10)
        Sf = np.where(
            A > 1e-10,
            self.n**2 * Q**2 / (A**2 * R**(4.0/3.0)),
            0.0
        )

        # S = [0, gA(S0 - Sf)]
        S[:, 0] = 0.0
        S[:, 1] = self.g * A * (self.S0 - Sf)

        return S

    def compute_rhs(self, U):
        """
         dU/dt = -1/dx[F(i+1/2) - F(i-1/2)] + S

        Args:
            U:  [ncells, 2]

        Returns:
            dU_dt:  [ncells, 2]
        """
        # 
        U_save = self.U.copy()
        self.U = U.copy()

        # 1. 
        U_L, U_R = self.reconstruct_interface_values()

        # 2. 
        F = self.compute_interface_flux(U_L, U_R)

        # 3. 
        S = self.compute_source_term()

        # 4. RHS
        dU_dt = np.zeros_like(U)

        for i in range(self.ncells):
            # 
            flux_diff = (F[i+1] - F[i]) / self.dx[i]

            # dU/dt = -flux_diff + S
            dU_dt[i] = -flux_diff + S[i]

        # 
        self.U = U_save

        return dU_dt

    def compute_cfl_timestep(self, cfl=0.5):
        """
        CFL

        dt <= CFL * min(dx / (|u| + c))

        Args:
            cfl: CFL (0.5 for Euler, 0.9 for RK2)

        Returns:
            dt:  [s]
        """
        h, u = self.get_primitive_variables()

        #  c = sqrt(g*h)
        c = np.sqrt(self.g * np.maximum(h, 1e-10))

        # 
        lambda_max = np.abs(u) + c

        # CFL
        dt_cfl = cfl * np.min(self.dx / np.maximum(lambda_max, 1e-10))

        return dt_cfl

    def step_euler(self, dt):
        """
        Euler

        U^(n+1) = U^n + dt * RHS(U^n)

        Args:
            dt:  [s]
        """
        dU_dt = self.compute_rhs(self.U)
        self.U += dt * dU_dt

    def step_ssp_rk2(self, dt):
        """
        SSP-RK2 (Strong Stability Preserving Runge-Kutta 2) 

        U* = U^n + dt * RHS(U^n)
        U^(n+1) = 0.5*U^n + 0.5*(U* + dt*RHS(U*))

        Args:
            dt:  [s]
        """
        U_n = self.U.copy()

        # 
        dU_dt_1 = self.compute_rhs(U_n)
        U_star = U_n + dt * dU_dt_1

        # 
        self.U = U_star.copy()
        dU_dt_2 = self.compute_rhs(U_star)
        U_new = 0.5 * U_n + 0.5 * (U_star + dt * dU_dt_2)

        self.U = U_new

    def step(self, dt):
        """
        

        Args:
            dt:  [s]
        """
        if self.time_integrator == 'euler':
            self.step_euler(dt)
        elif self.time_integrator == 'ssp_rk2':
            self.step_ssp_rk2(dt)

    def solve(self, t_end, dt=None, cfl=0.5, output_interval=None, verbose=True):
        """
        

        Args:
            t_end:  [s]
            dt:  [s]None
            cfl: CFL
            output_interval:  [s]None
            verbose: 

        Returns:
            history: {'t': [...], 'U': [...]} 
        """
        t = 0.0
        step_count = 0

        history = {'t': [0.0], 'U': [self.U.copy()]}

        if verbose:
            print(f"FVM (reconstruction={self.reconstruction}, riemann={self.riemann})")
            print(f"  : {t_end}s, CFL={cfl}")

        while t < t_end:
            # 
            if dt is None:
                dt_cfl = self.compute_cfl_timestep(cfl)
            else:
                dt_cfl = dt

            # 
            if t + dt_cfl > t_end:
                dt_cfl = t_end - t

            # 
            self.step(dt_cfl)
            t += dt_cfl
            step_count += 1

            # NaN
            if np.any(np.isnan(self.U)) or np.any(np.isinf(self.U)):
                raise RuntimeError(f" (NaN/Inf detected at t={t:.2f}s)")

            # 
            if output_interval is not None and step_count % max(1, int(output_interval / dt_cfl)) == 0:
                history['t'].append(t)
                history['U'].append(self.U.copy())

                if verbose and step_count % 100 == 0:
                    h, u = self.get_primitive_variables()
                    print(f"  t={t:.2f}s, dt={dt_cfl:.4f}s, h=[{h.min():.3f}, {h.max():.3f}]m")

        # 
        history['t'].append(t_end)
        history['U'].append(self.U.copy())

        if verbose:
            print(f"  ={step_count}")

        return history


# 
if __name__ == "__main__":
    print("=" * 70)
    print("FVM")
    print("=" * 70)
    print()

    # Dam break
    print(": Dam break ()")
    print()

    # 
    L = 100.0  # 
    nx = 101
    x = np.linspace(0, L, nx)

    # 
    B = 10.0
    S0 = 0.0
    n = 0.0  # 
    g = 9.81

    # 
    solver = FVMSolver(
        x_grid=x,
        B=B, S0=S0, n=n, g=g,
        reconstruction='muscl',
        limiter='minmod',
        riemann='hll',
        time_integrator='ssp_rk2'
    )

    # 
    h0 = np.where(solver.x_cell < 50.0, 2.0, 1.0)
    Q0 = np.zeros(solver.ncells)

    solver.initialize(h0, Q0)

    # 
    t_end = 5.0
    history = solver.solve(t_end, cfl=0.9, verbose=True)

    print()
    print("[OK] Dam break")
    print(f"  : {history['t'][-1]:.2f}s")
    print(f"  : {len(history['t'])}")

    h_final, u_final = solver.get_primitive_variables()
    print(f"  : [{h_final.min():.3f}, {h_final.max():.3f}]m")
    print(f"  : [{u_final.min():.3f}, {u_final.max():.3f}]m/s")
