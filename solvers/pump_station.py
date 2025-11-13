#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


HydrostaticCanalSolver


: Claude
: 2025-10-23
"""

import sys
import os
import numpy as np
from typing import Optional

# Add project root to path
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)

from solvers.gate import HydraulicStructure


class PumpStation(HydraulicStructure):
    """

    
    
    1. 
    2. 
    3. 

    
    - Q = Q_rated
    - Q = Q_rated * (h_upstream / h_min)^0.5
    - H_pump = H_rated
    """

    def __init__(self, position: float, width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 min_suction_head: float = 2.0,
                 g: float = 9.81):
        """
        Args:
            position:  (m)
            width:  (m)
            rated_flow:  (m³/s)
            rated_head:  (m)
            min_suction_head:  (m)
            g:  (m/s²)
        """
        super().__init__(position, width, g)
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.min_suction_head = min_suction_head

        # 
        self.is_running = True

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        

        
        1.  >= min_suction_headQ = Q_rated
        2.  < min_suction_headQ = Q_rated * sqrt(h_upstream / min_suction_head)
        3. 

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (discharge, flow_type):  (m³/s) 
        """
        if not self.is_running:
            return 0.0, 'pump_off'

        # 
        if h_upstream < 0.1:  # 
            return 0.0, 'insufficient_water'

        if h_upstream >= self.min_suction_head:
            # 
            discharge = self.rated_flow
            flow_type = 'rated'
        else:
            # 
            # Q = Q_rated * sqrt(h_up / h_min)
            ratio = np.sqrt(h_upstream / self.min_suction_head)
            discharge = self.rated_flow * ratio
            flow_type = 'reduced'

        return discharge, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        

        
        1. h >= h_mindQ/dh = 0
        2. h < h_mindQ/dh_up > 0
        3. dQ/dh_down = 0

        Args:
            h_upstream:  (m)
            h_downstream:  (m)
            t:  (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 
        """
        if not self.is_running or h_upstream < 0.1:
            return 0.0, 0.0

        if h_upstream >= self.min_suction_head:
            # 
            dQ_dh_up = 0.0
        else:
            # Q = Q_rated * sqrt(h_up / h_min)
            # dQ/dh_up = Q_rated / (2 * sqrt(h_up * h_min))
            dQ_dh_up = self.rated_flow / (2.0 * np.sqrt(h_upstream * self.min_suction_head))

        # 
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def set_running_state(self, is_running: bool):
        """
        

        Args:
            is_running: True=False=
        """
        self.is_running = is_running

    def __repr__(self) -> str:
        state = "ON" if self.is_running else "OFF"
        return (f"PumpStation(position={self.position}m, Q_rated={self.rated_flow}m³/s, "
                f"H_rated={self.rated_head}m, state={state})")


if __name__ == "__main__":
    """"""
    print("=" * 80)
    print("PumpStation Class Test")
    print("=" * 80)

    # 
    pump = PumpStation(
        position=5000.0,
        width=10.0,
        rated_flow=30.0,
        rated_head=5.0,
        min_suction_head=2.0
    )

    print(f"\n:")
    print(f"  {pump}")
    print(f"  : {pump.rated_flow} m³/s")
    print(f"  : {pump.rated_head} m")
    print(f"  : {pump.min_suction_head} m")
    print()

    # 
    print(":")
    print(f"{'(m)':>12} {'(m³/s)':>12} {'':>15} {'dQ/dh_up':>12}")
    print("-" * 55)

    h_ups = [0.05, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
    h_down = 3.0  # 

    for h_up in h_ups:
        Q, flow_type = pump.calculate_discharge(h_up, h_down)
        dQ_up, dQ_down = pump.calculate_discharge_derivatives(h_up, h_down)
        print(f"{h_up:12.2f} {Q:12.2f} {flow_type:>15} {dQ_up:12.4f}")

    # 
    print(f"\n:")
    print(f"  : ")
    Q_on, _ = pump.calculate_discharge(3.0, 3.0)
    print(f"  : {Q_on:.2f} m³/s")

    pump.set_running_state(False)
    print(f"  ...")
    Q_off, _ = pump.calculate_discharge(3.0, 3.0)
    print(f"  : {Q_off:.2f} m³/s")

    pump.set_running_state(True)
    print(f"  ...")
    Q_on2, _ = pump.calculate_discharge(3.0, 3.0)
    print(f"  : {Q_on2:.2f} m³/s")

    print(f"\n!")
    print("=" * 80)
