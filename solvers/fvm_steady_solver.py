#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FVM

NewtonSaint-Venant


- dU/dt = 0
- R(U) = -1/dx[F(i+1/2) - F(i-1/2)] + S(U) = 0
- NewtonJ*dU = -RJJacobian

: Claude
: 2025-10-23
"""

import numpy as np
from scipy.sparse import diags, csr_matrix
from scipy.sparse.linalg import spsolve
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.riemann_solvers import hll_flux_shallow_water
from utils.canal_utils import compute_steady_uniform_flow


class FVMSteadySolver:
    """
    FVM

    NewtonSaint-Venant
    """

    def __init__(self, x_grid, B, S0, n, g=9.81, gates=None):
        """
        

        Args:
            x_grid:  [m]
            B:  [m]
            S0:  [-]
            n: Manning [s/m^(1/3)]
            g:  [m/s²]
            gates:  [(position, opening, Cd), ...]
        """
        self.x = np.array(x_grid)
        self.nx = len(self.x)
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g

        # 
        self.x_cell = 0.5 * (self.x[:-1] + self.x[1:])
        self.dx = np.diff(self.x)
        self.ncells = len(self.x_cell)

        #  U = [A, Q]
        self.U = np.zeros((self.ncells, 2))

        # 
        self.gates = gates if gates is not None else []
        self.gate_interfaces = []

        for gate_pos, gate_opening, gate_Cd in self.gates:
            interface_idx = np.argmin(np.abs(self.x - gate_pos))
            self.gate_interfaces.append({
                'index': interface_idx,
                'position': gate_pos,
                'actual_x': self.x[interface_idx],
                'opening': gate_opening,
                'Cd': gate_Cd
            })

        if len(self.gates) > 0:
            print(f"\nFVM:")
            print(f"  {len(self.gates)}")
            for i, gate_info in enumerate(self.gate_interfaces):
                print(f"  {i+1}: x={gate_info['position']}m ({gate_info['index']}), "
                      f"={gate_info['opening']}m, Cd={gate_info['Cd']}")

    def initialize(self, h0, Q0):
        """
        

        Args:
            h0:  [m] ()
            Q0:  [m³/s] ()
        """
        if np.isscalar(h0):
            h0 = np.ones(self.ncells) * h0
        if np.isscalar(Q0):
            Q0 = np.ones(self.ncells) * Q0

        self.U[:, 0] = self.B * np.array(h0)  # A = B * h
        self.U[:, 1] = np.array(Q0)

    def compute_interface_flux(self, U):
        """
        

        Args:
            U:  [ncells, 2]

        Returns:
            F:  [ncells+1, 2]
        """
        F = np.zeros((self.ncells + 1, 2))

        # 
        gate_indices = {g['index']: g for g in self.gate_interfaces}

        for i in range(1, self.ncells):
            # 
            U_L = U[i-1]
            U_R = U[i]

            # 
            if i in gate_indices:
                # 
                gate_info = gate_indices[i]
                F[i] = self._compute_gate_flux(U_L, U_R, gate_info)
            else:
                # HLL Riemann
                F[i] = hll_flux_shallow_water(U_L, U_R, self.B, self.g)

        return F

    def _compute_gate_flux(self, U_L, U_R, gate_info):
        """
        

        Args:
            U_L, U_R:  [A, Q]
            gate_info: 

        Returns:
            F:  [F_mass, F_momentum]
        """
        A_L, Q_L = U_L
        A_R, Q_R = U_R

        h_L = A_L / self.B if A_L > 1e-10 else 1e-10
        h_R = A_R / self.B if A_R > 1e-10 else 1e-10

        a = gate_info['opening']
        Cd = gate_info['Cd']

        # 
        delta_h = h_L - h_R

        if h_L > a:
            # 
            if delta_h > 0:
                Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * delta_h)
            else:
                Q_gate = 0.0
        else:
            # 
            Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * h_L)

        # 
        F_mass = Q_gate

        # 
        A_avg = 0.5 * (A_L + A_R)
        h_avg = 0.5 * (h_L + h_R)
        u_gate = Q_gate / A_avg if A_avg > 1e-10 else 0.0

        F_momentum = Q_gate * u_gate + 0.5 * self.g * A_avg * h_avg

        return np.array([F_mass, F_momentum])

    def compute_source_term(self, U):
        """
         S = [0, gA(S0 - Sf)]

        Args:
            U:  [ncells, 2]

        Returns:
            S:  [ncells, 2]
        """
        S = np.zeros_like(U)

        A = U[:, 0]
        Q = U[:, 1]

        h = A / self.B
        h = np.maximum(h, 1e-10)  # 

        # Manning
        R = self.B * h / (self.B + 2 * h)  # 
        R = np.maximum(R, 1e-10)

        Sf = np.zeros_like(h)
        mask = A > 1e-10
        Sf[mask] = self.n**2 * Q[mask]**2 / (A[mask]**2 * R[mask]**(4.0/3.0))

        # 
        S[:, 0] = 0.0
        S[:, 1] = self.g * A * (self.S0 - Sf)

        return S

    def compute_steady_residual(self, U, Q_upstream, h_downstream):
        """
        

        dU/dt = 0
        => -1/dx[F(i+1/2) - F(i-1/2)] + S = 0

        Args:
            U:  [ncells, 2]
            Q_upstream: 
            h_downstream: 

        Returns:
            R:  [ncells, 2]
        """
        R = np.zeros_like(U)

        # 
        F = self.compute_interface_flux(U)

        # 
        #  (i=0)
        A_upstream = U[0, 0]
        h_upstream = A_upstream / self.B
        u_upstream = Q_upstream / A_upstream if A_upstream > 1e-10 else 0.0
        F[0] = np.array([
            Q_upstream,
            Q_upstream * u_upstream + 0.5 * self.g * A_upstream * h_upstream
        ])

        #  (i=ncells)
        A_downstream = self.B * h_downstream
        Q_downstream = U[-1, 1]
        u_downstream = Q_downstream / A_downstream if A_downstream > 1e-10 else 0.0
        F[-1] = np.array([
            Q_downstream,
            Q_downstream * u_downstream + 0.5 * self.g * A_downstream * h_downstream
        ])

        # 
        S = self.compute_source_term(U)

        # 
        for i in range(self.ncells):
            flux_diff = (F[i+1] - F[i]) / self.dx[i]
            R[i] = -flux_diff + S[i]

        return R

    def solve_steady_newton(self, Q_target, h_downstream=None,
                           max_iter=50, tol=1e-6, verbose=True):
        """
        Newton

        Args:
            Q_target:  [m³/s]
            h_downstream:  [m]None
            max_iter: 
            tol: 
            verbose: 

        Returns:
            converged: 
        """
        if h_downstream is None:
            h_downstream = compute_steady_uniform_flow(Q_target, self.B, self.S0, self.n, self.g)

        if verbose:
            print(f"\nNewton...")
            print(f"  : {Q_target} m³/s")
            print(f"  : {h_downstream:.3f} m")
            print(f"  : {tol}")
            print()

        for iter_count in range(max_iter):
            # 
            R = self.compute_steady_residual(self.U, Q_target, h_downstream)

            # 
            residual_norm = np.linalg.norm(R)

            if verbose and iter_count % 5 == 0:
                Q_avg = np.mean(self.U[:, 1])
                Q_error = abs(Q_avg - Q_target) / Q_target * 100
                print(f"  Iter {iter_count:3d}: ||R||={residual_norm:.6e}, "
                      f"Q_avg={Q_avg:.4f} m³/s, error={Q_error:.4f}%")

            # 
            if residual_norm < tol:
                if verbose:
                    print(f"\n[OK] Newton(iter={iter_count}, ||R||={residual_norm:.6e})")
                return True

            # Jacobian
            dU = self._newton_step_fd(R, Q_target, h_downstream)

            # 
            relax = 0.5  # 
            self.U = self.U + relax * dU

            # 
            self.U[:, 0] = np.maximum(self.U[:, 0], self.B * 0.01)  # A > 0

        if verbose:
            print(f"\n[WARN] Newton{max_iter}")
            print(f"  : ||R||={residual_norm:.6e}")

        return False

    def _newton_step_fd(self, R, Q_upstream, h_downstream, epsilon=1e-6):
        """
        Newton

        Jacobian

        Args:
            R: 
            Q_upstream: 
            h_downstream: 
            epsilon: 

        Returns:
            dU: Newton
        """
        dU = np.zeros_like(self.U)

        # 
        for i in range(self.ncells):
            for j in range(2):
                # 
                U_perturb = self.U.copy()
                U_perturb[i, j] += epsilon

                # 
                R_perturb = self.compute_steady_residual(U_perturb, Q_upstream, h_downstream)

                #  (Jacobian)
                dR_dU = (R_perturb[i, j] - R[i, j]) / epsilon

                # Newton
                if abs(dR_dU) > 1e-10:
                    dU[i, j] = -R[i, j] / dR_dU
                else:
                    dU[i, j] = 0.0

        return dU

    def get_results(self):
        """
        

        Returns:
            dict: x, h, Q, u
        """
        h = self.U[:, 0] / self.B
        Q = self.U[:, 1]
        u = Q / (self.B * h)

        return {
            'x': self.x_cell,
            'h': h,
            'Q': Q,
            'u': u
        }
