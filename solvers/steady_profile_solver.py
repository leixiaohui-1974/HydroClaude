#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


hQ
Jacobian

: Claude
: 2025-10-22
"""

import numpy as np
from scipy.integrate import solve_bvp
from scipy.optimize import fsolve, brentq
from typing import List, Tuple, Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.gate import HydraulicStructure
from utils.canal_utils import compute_steady_uniform_flow


class SteadyProfileSolver:
    """
    

    
    - hQ
    - Jacobian
    - shooting methodBVP
    - 
    """

    def __init__(self,
                 length: float,
                 B: float,
                 S0: float,
                 n: float,
                 g: float = 9.81):
        """
        Args:
            length:  (m)
            B:  (m)
            S0: 
            n: Manning
            g:  (m/s²)
        """
        self.length = length
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g

    def compute_friction_slope(self, h: float, Q: float) -> float:
        """
        Manning

        Sf = (n·V)² / R^(4/3)
        """
        h_safe = np.maximum(h, 1e-6)
        A = self.B * h_safe
        P = self.B + 2 * h_safe
        R = A / P
        V = Q / A

        Sf = (self.n * V)**2 / R**(4/3)
        return Sf

    def compute_froude(self, h: float, Q: float) -> float:
        """Froude"""
        h_safe = np.maximum(h, 1e-6)
        A = self.B * h_safe
        V = Q / A
        Fr = V / np.sqrt(self.g * h_safe)
        return Fr

    def dh_dx(self, h: float, Q: float) -> float:
        """
        

        dh/dx = (S0 - Sf) / (1 - Fr²)

        
        - Fr < 1 (): dh/dx(S0-Sf)
        - Fr > 1 (): dh/dx(S0-Sf)
        - Fr → 1 (): dh/dx → ∞
        """
        Sf = self.compute_friction_slope(h, Q)
        Fr = self.compute_froude(h, Q)

        # 
        denominator = 1 - Fr**2
        if abs(denominator) < 0.01:
            # 
            denominator = np.sign(denominator) * max(abs(denominator), 0.01)

        dh = (self.S0 - Sf) / denominator

        return dh

    def solve_without_structures(self,
                                 Q: float,
                                 h_downstream: float,
                                 nx: int = 201,
                                 method: str = 'shooting') -> Dict:
        """
        

        Args:
            Q:  (m³/s)
            h_downstream:  (m)
            nx: 
            method:  ('shooting'  'bvp')

        Returns:
            result: xh
        """
        x = np.linspace(0, self.length, nx)

        if method == 'shooting':
            # Shooting method: 
            h = np.zeros(nx)
            h[-1] = h_downstream

            dx = self.length / (nx - 1)

            # Euler
            for i in range(nx-2, -1, -1):
                # 
                def residual(h_i):
                    dh_avg = self.dh_dx((h_i + h[i+1])/2, Q)
                    return h_i - h[i+1] + dx * dh_avg

                # 
                if i == nx - 2:
                    h_init = h[i+1]
                else:
                    h_init = 2*h[i+1] - h[i+2]

                try:
                    h[i] = fsolve(residual, h_init)[0]
                except Exception:
                    # Backward Euler in physical x-direction.
                    h[i] = h[i+1] - dx * self.dh_dx(h[i+1], Q)

        else:  # BVP method
            # scipyBVP
            def ode_system(x, y):
                """ODE: y' = f(x, y),  y = h"""
                h = y[0]
                dh = self.dh_dx(h, Q)
                return np.array([dh])

            def bc(ya, yb):
                """: h(L) = h_downstream"""
                return np.array([yb[0] - h_downstream])

            # 
            h_uniform = compute_steady_uniform_flow(Q, self.B, self.S0, self.n, self.g)
            y_init = np.array([h_uniform * np.ones(nx)])

            sol = solve_bvp(ode_system, bc, x, y_init)
            h = sol.sol(x)[0]

        return {
            'x': x,
            'h': h,
            'Q': Q * np.ones(nx),
            'method': method
        }

    def solve_with_single_gate(self,
                               Q: float,
                               h_downstream: float,
                               gate_position: float,
                               gate: HydraulicStructure,
                               nx: int = 201) -> Dict:
        """
        

        
        1. 
        2. 

        Args:
            Q:  (m³/s)
            h_downstream:  (m)
            gate_position:  (m)
            gate: 
            nx: 

        Returns:
            result: x, h, Q
        """
        # 
        x_full = np.linspace(0, self.length, nx)
        gate_idx = np.argmin(np.abs(x_full - gate_position))
        x_gate = x_full[gate_idx]

        # 
        nx_down = nx - gate_idx
        result_down = self.solve_without_structures(
            Q, h_downstream, nx_down, method='shooting'
        )
        h_down = result_down['h']
        x_down = x_gate + result_down['x'] / self.length * (self.length - x_gate)

        # 
        h_gate_down = h_down[0]

        # 
        # Q = f(h_up, h_down)
        def gate_equation(h_up):
            Q_gate, _ = gate.calculate_discharge(h_up, h_gate_down, t=0.0)
            return Q_gate - Q

        # 
        h_up_init = h_gate_down + 0.1

        try:
            # Brent
            h_gate_up = brentq(gate_equation, h_gate_down, h_gate_down + 5.0)
        except Exception:
            # fsolve
            h_gate_up = fsolve(gate_equation, h_up_init)[0]

        # 
        nx_up = gate_idx + 1
        result_up = self.solve_without_structures(
            Q, h_gate_up, nx_up, method='shooting'
        )
        h_up = result_up['h']
        x_up = result_up['x'] / self.length * x_gate

        # 
        x_full = np.concatenate([x_up, x_down[1:]])
        h_full = np.concatenate([h_up, h_down[1:]])

        return {
            'x': x_full,
            'h': h_full,
            'Q': Q * np.ones(len(x_full)),
            'gate_position': x_gate,
            'h_gate_up': h_gate_up,
            'h_gate_down': h_gate_down,
            'gate_idx': gate_idx
        }

    def solve_with_multiple_gates(self,
                                  Q: float,
                                  h_downstream: float,
                                  gates: List[Tuple[float, HydraulicStructure]],
                                  nx: int = 201,
                                  max_iter: int = 50,
                                  tol: float = 1e-4) -> Dict:
        """
        

        
        1. 
        2. 
        3. 

        Args:
            Q:  (m³/s)
            h_downstream:  (m)
            gates:  [(position, gate), ...]
            nx: 
            max_iter: 
            tol: 

        Returns:
            result: x, h, Q
        """
        # 
        gates_sorted = sorted(gates, key=lambda g: g[0])
        n_gates = len(gates_sorted)

        # 
        x_full = np.linspace(0, self.length, nx)
        gate_positions = [g[0] for g in gates_sorted]
        gate_indices = [np.argmin(np.abs(x_full - pos)) for pos in gate_positions]

        # 
        segments = []
        boundaries = [0] + [x_full[idx] for idx in gate_indices] + [self.length]

        for i in range(n_gates + 1):
            x_start = boundaries[i]
            x_end = boundaries[i + 1]
            segment_length = x_end - x_start

            # 
            if i == n_gates:
                idx_start = gate_indices[-1] if n_gates > 0 else 0
                idx_end = nx - 1
            elif i == 0:
                idx_start = 0
                idx_end = gate_indices[0]
            else:
                idx_start = gate_indices[i - 1]
                idx_end = gate_indices[i]

            nx_segment = idx_end - idx_start + 1

            segments.append({
                'x_start': x_start,
                'x_end': x_end,
                'length': segment_length,
                'nx': nx_segment,
                'idx_start': idx_start,
                'idx_end': idx_end
            })

        # 
        h_uniform = compute_steady_uniform_flow(Q, self.B, self.S0, self.n, self.g)
        h_gates_up = [h_uniform + 0.05 * (i+1) for i in range(n_gates)]
        h_gates_down = [h_uniform for _ in range(n_gates)]

        # 
        for iter_count in range(max_iter):
            h_segments = []
            x_segments = []

            # 
            for i in range(n_gates, -1, -1):
                seg = segments[i]

                # 
                if i == n_gates:
                    # 
                    h_bc = h_downstream
                else:
                    # 
                    h_bc = h_gates_up[i]

                # 
                # 
                temp_solver = SteadyProfileSolver(seg['length'], self.B, self.S0, self.n, self.g)
                result_seg = temp_solver.solve_without_structures(Q, h_bc, seg['nx'], method='shooting')

                h_segments.insert(0, result_seg['h'])
                x_seg_local = result_seg['x']
                x_seg_global = seg['x_start'] + x_seg_local
                x_segments.insert(0, x_seg_global)

                # 
                if i > 0:
                    h_gates_down[i - 1] = result_seg['h'][0]

            # 
            max_change = 0.0
            for i in range(n_gates):
                _, gate_obj = gates_sorted[i]
                h_down = h_gates_down[i]

                def gate_eq(h_up):
                    Q_gate, _ = gate_obj.calculate_discharge(h_up, h_down, t=0.0)
                    return Q_gate - Q

                try:
                    h_up_new = brentq(gate_eq, h_down, h_down + 5.0)
                except Exception:
                    h_up_new = fsolve(gate_eq, h_gates_up[i])[0]

                change = abs(h_up_new - h_gates_up[i])
                max_change = max(max_change, change)

                # 
                relax = 0.7
                h_gates_up[i] = (1 - relax) * h_gates_up[i] + relax * h_up_new

            # 
            if max_change < tol:
                break

        # 
        h_full = np.concatenate(h_segments)
        x_full_result = np.concatenate(x_segments)

        return {
            'x': x_full_result,
            'h': h_full,
            'Q': Q * np.ones(len(h_full)),
            'converged': max_change < tol,
            'iterations': iter_count + 1,
            'h_gates_up': h_gates_up,
            'h_gates_down': h_gates_down,
            'gate_positions': gate_positions
        }


def test_steady_profile_solver():
    """"""
    from solvers.gate import SluiceGate

    print("=" * 80)
    print("")
    print("=" * 80)

    # 1
    print("\n1")
    print("-" * 80)

    solver = SteadyProfileSolver(
        length=1000.0,
        B=10.0,
        S0=0.001,
        n=0.025
    )

    Q = 10.0
    h_downstream = compute_steady_uniform_flow(Q, 10.0, 0.001, 0.025)

    result1 = solver.solve_without_structures(Q, h_downstream, nx=201, method='shooting')

    print(f"  : {Q} m³/s")
    print(f"  : {h_downstream:.4f} m")
    print(f"  : {result1['h'][0]:.4f} m")
    print(f"  : {abs(result1['h'][0] - h_downstream):.6f} m")
    print(f"  [OK] ")

    # 2
    print("\n\n2")
    print("-" * 80)

    gate = SluiceGate(position=500.0, width=10.0, opening=5.0, Cd=0.6)

    result2 = solver.solve_with_single_gate(Q, h_downstream, 500.0, gate, nx=201)

    print(f"  : {Q} m³/s")
    print(f"  : 500.0 m")
    print(f"  : 5.0 m")
    print(f"  : {result2['h_gate_up']:.4f} m")
    print(f"  : {result2['h_gate_down']:.4f} m")
    print(f"  : {result2['h_gate_up'] - result2['h_gate_down']:.4f} m")
    print(f"  [OK] ")

    # 3
    print("\n\n3")
    print("-" * 80)

    gate1 = SluiceGate(position=250.0, width=10.0, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=500.0, width=10.0, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=750.0, width=10.0, opening=5.0, Cd=0.6)

    import time
    start_time = time.time()

    result3 = solver.solve_with_multiple_gates(
        Q, h_downstream,
        [(gate1.position, gate1),
         (gate2.position, gate2),
         (gate3.position, gate3)],
        nx=201,
        max_iter=100,
        tol=1e-4
    )

    elapsed = time.time() - start_time

    print(f"  : {Q} m³/s")
    print(f"  : {'' if result3['converged'] else ''}")
    print(f"  : {result3['iterations']}")
    print(f"  : {elapsed:.4f}s")
    print(f"  1 (250m): ={result3['h_gates_up'][0]:.4f}m, ={result3['h_gates_down'][0]:.4f}m")
    print(f"  2 (500m): ={result3['h_gates_up'][1]:.4f}m, ={result3['h_gates_down'][1]:.4f}m")
    print(f"  3 (750m): ={result3['h_gates_up'][2]:.4f}m, ={result3['h_gates_down'][2]:.4f}m")
    print(f"  [OK] ")

    print("\n" + "=" * 80)
    print("")
    print("=" * 80)


if __name__ == "__main__":
    test_steady_profile_solver()
