#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""





: Claude
: 2025-10-22
"""

import numpy as np
from typing import List, Dict, Optional
import sys
import os

# 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.canal_solver import CanalSolver
from solvers.gate import HydraulicStructure
from utils.canal_utils import compute_steady_uniform_flow


class CoupledCanalSolver:
    """
    

    
    
    """

    def __init__(self,
                 total_length: float,
                 structures: List[HydraulicStructure],
                 nx_total: int = 201,
                 B: float = 10.0,
                 S0: float = 0.001,
                 n: float = 0.025,
                 g: float = 9.81,
                 method: str = 'preissmann',
                 coupling_max_iter: int = 20,
                 coupling_tol: float = 0.01,
                 coupling_relax: float = 0.3):
        """
        Args:
            total_length:  (m)
            structures: 
            nx_total: 
            B:  (m)
            S0: 
            n: Manning
            g:  (m/s²)
            method:  ('explicit', 'preissmann', 'hll')
            coupling_max_iter: 
            coupling_tol:  (m³/s)
            coupling_relax:  (0-1)
        """
        self.total_length = total_length
        self.structures = sorted(structures, key=lambda s: s.position)
        self.nx_total = nx_total
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.method = method

        # 
        self.coupling_max_iter = coupling_max_iter
        self.coupling_tol = coupling_tol
        self.coupling_relax = coupling_relax

        # 
        self._create_segments()

        # 
        self.structure_flows = [0.0] * len(self.structures)

    def _create_segments(self):
        """"""
        # 
        positions = [0.0] + [s.position for s in self.structures] + [self.total_length]

        self.segments = []
        self.segment_lengths = []

        # 
        for i in range(len(positions) - 1):
            length = positions[i+1] - positions[i]
            self.segment_lengths.append(length)

            # 
            nx_segment = max(11, int(self.nx_total * length / self.total_length))
            if nx_segment % 2 == 0:  # 
                nx_segment += 1

            segment = CanalSolver(
                length=length,
                nx=nx_segment,
                B=self.B,
                S0=self.S0,
                n=self.n,
                g=self.g,
                method=self.method
            )

            self.segments.append(segment)

    def reset_with_steady_state(self, Q0: float) -> float:
        """
        

        Args:
            Q0:  (m³/s)

        Returns:
             (m)
        """
        h_uniform = compute_steady_uniform_flow(Q0, self.B, self.S0, self.n, self.g)

        for segment in self.segments:
            segment.reset_with_steady_state(Q0)

        # 
        self.structure_flows = [Q0] * len(self.structures)

        return h_uniform

    def step_steady(self, dt: float, Q_upstream: float, h_downstream: float,
                   max_iterations: int = 500, verbose: bool = False) -> Dict:
        """
        

        

        Args:
            dt:  (s)
            Q_upstream:  (m³/s)
            h_downstream:  (m) - None
            max_iterations: 
            verbose: 

        Returns:
            
        """
        # 
        if h_downstream is None:
            h_downstream = compute_steady_uniform_flow(Q_upstream, self.B, self.S0, self.n, self.g)

        converged = False

        for iter_count in range(max_iterations):
            # 
            Q_bc_up = Q_upstream

            for i, segment in enumerate(self.segments):
                # 
                Q_up = Q_bc_up

                # 
                if i == len(self.segments) - 1:
                    # 
                    h_down = h_downstream
                else:
                    # 
                    structure = self.structures[i]
                    Q_gate = self.structure_flows[i]

                    # 
                    h_gate_down = self.segments[i+1].h[0]

                    # 
                    if isinstance(structure, type(structure)) and hasattr(structure, 'opening'):
                        # Q = Cd * B * e * sqrt(2*g*delta_h)
                        C = structure.Cd * structure.width * structure.opening
                        if Q_gate > 1e-6:
                            delta_h = (Q_gate / C) ** 2 / (2 * structure.g)
                        else:
                            delta_h = 1e-4
                        h_down = h_gate_down + delta_h
                    else:
                        # 
                        h_down = h_gate_down + 0.01

                # 
                segment.step(dt, Q_up, h_down)

                # 
                if i < len(self.structures):
                    structure = self.structures[i]
                    h_up = segment.h[-1]
                    h_dn = self.segments[i+1].h[0]

                    Q_gate_new, _ = structure.calculate_discharge(h_up, h_dn)

                    # 
                    Q_gate_old = self.structure_flows[i]
                    if abs(Q_gate_new - Q_gate_old) > self.coupling_tol:
                        # 
                        self.structure_flows[i] = (
                            Q_gate_old * (1 - self.coupling_relax) +
                            Q_gate_new * self.coupling_relax
                        )
                    else:
                        self.structure_flows[i] = Q_gate_new

                    # 
                    Q_bc_up = self.structure_flows[i]

            # 
            if iter_count > 50:  # 50
                all_converged = True
                for i, structure in enumerate(self.structures):
                    h_up = self.segments[i].h[-1]
                    h_dn = self.segments[i+1].h[0]
                    Q_calc, _ = structure.calculate_discharge(h_up, h_dn)

                    if abs(Q_calc - self.structure_flows[i]) > self.coupling_tol:
                        all_converged = False
                        break

                if all_converged:
                    # 
                    Q_errors = []
                    for seg in self.segments:
                        Q_avg = np.mean(seg.Q[1:-1])
                        Q_errors.append(abs(Q_avg - Q_upstream) / Q_upstream)

                    if max(Q_errors) < 0.001:  # < 0.1%
                        converged = True
                        if verbose:
                            print(f"[OK]  (iter={iter_count+1})")
                        break

        return {
            'converged': converged,
            'iterations': iter_count + 1,
            'structure_flows': self.structure_flows.copy(),
            'Q_errors': Q_errors if converged else None
        }

    def step(self, dt: float, Q_upstream: float, h_downstream: Optional[float] = None):
        """
        

        -
        1. 
        2. 
        3. 

        Args:
            dt:  (s)
            Q_upstream:  (m³/s)
            h_downstream:  (m) - None
        """
        # 
        Q_gates_pred = self.structure_flows.copy()

        # 
        Q_bc_up = Q_upstream

        for i, segment in enumerate(self.segments):
            # 
            Q_up = Q_bc_up

            # 
            if i == len(self.segments) - 1:
                # 
                if h_downstream is None:
                    # 
                    Q_avg = np.mean(segment.Q[1:-1])
                    h_down = compute_steady_uniform_flow(Q_avg, self.B, self.S0, self.n, self.g)
                else:
                    h_down = h_downstream
            else:
                # 
                # 
                structure = self.structures[i]
                Q_gate_pred = Q_gates_pred[i]
                h_gate_down = self.segments[i+1].h[0]

                # Q_gateh_down
                if hasattr(structure, 'opening'):
                    C = structure.Cd * structure.width * structure.opening
                    if Q_gate_pred > 1e-6:
                        delta_h_required = (Q_gate_pred / C) ** 2 / (2 * structure.g)
                    else:
                        delta_h_required = 1e-4
                    h_down = h_gate_down + delta_h_required
                else:
                    h_down = h_gate_down + 0.01

            # 
            segment.step(dt, Q_up, h_down)

            # 
            if i < len(self.structures):
                structure = self.structures[i]
                h_up_actual = segment.h[-1]
                h_dn_actual = self.segments[i+1].h[0]

                # 
                Q_gate_calc, _ = structure.calculate_discharge(h_up_actual, h_dn_actual)

                # 
                # Q_gate
                alpha = 0.5  # 
                Q_gate_new = Q_gates_pred[i] * (1 - alpha) + Q_gate_calc * alpha

                # 
                self.structure_flows[i] = Q_gate_new

                # 
                Q_bc_up = Q_gate_new

    def get_full_profile(self) -> Dict[str, np.ndarray]:
        """
        

        Returns:
            x, h, Q
        """
        x_list = []
        h_list = []
        Q_list = []

        x_offset = 0.0
        for i, segment in enumerate(self.segments):
            # 
            if i < len(self.segments) - 1:
                x_list.append(segment.x[:-1] + x_offset)
                h_list.append(segment.h[:-1])
                Q_list.append(segment.Q[:-1])
            else:
                x_list.append(segment.x + x_offset)
                h_list.append(segment.h)
                Q_list.append(segment.Q)

            x_offset += segment.length

        return {
            'x': np.concatenate(x_list),
            'h': np.concatenate(h_list),
            'Q': np.concatenate(Q_list),
        }

    def clear_history(self):
        """"""
        for segment in self.segments:
            segment.clear_history()

    def __repr__(self) -> str:
        return (f"CoupledCanalSolver(length={self.total_length}m, "
                f"segments={len(self.segments)}, structures={len(self.structures)})")
